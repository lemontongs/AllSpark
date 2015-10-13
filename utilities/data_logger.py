import os
import sys
import csv
import time
import datetime
import logging
from threading import Lock

logger = logging.getLogger('allspark.data_logger')

class Data_Logger():
    def __init__(self, log_directory, filename, archive_prefix, data_item_names):
        self._initialized = False
        self.mutex = Lock()
        self.archive_prefix = archive_prefix
        self.filename = filename
        self.data_item_names = data_item_names
        
        # Create the log directory if it does not exist
        self.log_directory = log_directory
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)
        
        self.last_day = time.localtime().tm_mday
        
        self._initialized = True
        
        self.setup_data_file()
    
    def isInitialized(self):
        return self._initialized
    
    def setup_data_file(self):
        if not self._initialized:
            logger.error( "setup_data_file called before _initialized." )
            return
        
        today = datetime.date.today().strftime( self.archive_prefix + '_%Y_%m_%d.csv' )
        todays_filename = self.log_directory + "/" + today
        
        # If the file is currently open, close it
        if hasattr(self, 'file_handle') and not self.file_handle.closed:
            self.file_handle.close()
        
        # If the "today" link exists, delete it
        if os.path.islink(self.filename):
            os.unlink(self.filename)
        
        # Touch todays data file (does nothing if it already exists)
        open(todays_filename, 'a').close()
        
        # Create the "today" link to todays data file
        os.symlink(today, self.filename)
        
        # Open the link as a data file
        try:
            self.file_handle = open(self.filename, 'a+')
            self.file_handle.seek(0,2)
        except:
            logger.error( "Failed to open "+ self.filename +" : " + repr(sys.exc_info()[1]) )
            return
        
    
    def add_data(self, data): # data should be an array of strings
        
        if not self._initialized:
            logger.error( "add_data called before _initialized." )
            return
        
        self.mutex.acquire()
        
        # Check if file needs to be changed
        now = time.time()
        if time.localtime(now).tm_mday != self.last_day:
            self.last_day = time.localtime(now).tm_mday
            self.setup_data_file()
        
        # Write to the file
        self.file_handle.write(str(now))
        for item in data:
            self.file_handle.write( "," + item )
        self.file_handle.write("\n")
        self.file_handle.flush()
        
        self.mutex.release()
        
        
    def get_google_chart_string(self, days=1, seconds=0):
        
        # start_time is "now" minus days and seconds
        # only this much data willl be shown
        start_time = datetime.datetime.now() - datetime.timedelta(days,seconds)
        
        # Load the data from the file
        self.mutex.acquire()
        file_handle = open(self.filename, 'r')
        csvreader = csv.reader(file_handle)
        lines = 0
        datalist = []
        for row in csvreader:
            datalist.append(row)
            lines += 1
        self.mutex.release()
        
        # Build the return string
        return_string = ""
        
        # Skip the ones before the start_time
        start_index = len(datalist)
        for i, row in enumerate(datalist):
            dt = datetime.datetime.fromtimestamp(float(row[0]))
            if dt > start_time:
                start_index = i
                break
        
        # Process the remaining data into a usable structure
        processed_data = []
        for i, row in enumerate(datalist[start_index:]):
            
            dt = datetime.datetime.fromtimestamp(float(row[0]))
            
            year   = dt.strftime('%Y')
            month  = str(int(dt.strftime('%m')) - 1) # javascript expects month in 0-11, strftime gives 1-12 
            day    = dt.strftime('%d')
            hour   = dt.strftime('%H')
            minute = dt.strftime('%M')
            second = dt.strftime('%S')
            
            time = 'new Date(%s,%s,%s,%s,%s,%s)' % (year,month,day,hour,minute,second)
            
            temp = {}
            temp["time"] = time
            for item in self.data_item_names:
                if item in row:
                    temp[item] = "1"
            
            processed_data.append( temp )
        
        if len(processed_data) == 0:
            return "[] // None available"
        
        # Save the first state
        start_times = {} 
        for item in self.data_item_names:
            if item in processed_data[0]:
                start_times[item] = processed_data[0]["time"]
            else:
                start_times[item] = None
        
        # Go through the processed data and write out a string whenever the user
        # is no longer present.
        for i, row in enumerate(processed_data[1:]):
            for item in self.data_item_names:
                if start_times[item] == None and (item in row):
                    start_times[item] = processed_data[i]["time"]
                if start_times[item] != None and (not (item in row)):
                    # write a string
                    return_string += ("['%s',  %s, %s],\n" % (item,  \
                                                              start_times[item],  \
                                                              row["time"]))
                    # set start time to None
                    start_times[item] = None
        
        for item in self.data_item_names:
            if start_times[item] != None:
                return_string += ("['%s',  %s, %s],\n" % (item,  \
                                                          start_times[item],  \
                                                          processed_data[-1]["time"]))
        # Remove the trailing comma and return line    
        if len(return_string) > 2:
            return_string = return_string[:-2]
        
        return return_string


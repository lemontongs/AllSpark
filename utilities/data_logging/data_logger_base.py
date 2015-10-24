
import os
import sys
import time
import datetime
import logging
from threading import Lock

logger = logging.getLogger('allspark.data_logger')

class Data_Logger():
    def __init__(self, data_directory, archive_prefix):
        self._initialized = False
        self.mutex = Lock()
        self.archive_prefix = archive_prefix
        self.filename = data_directory + "/today.csv"
                
        # Create the log directory if it does not exist
        self.data_directory = data_directory
        if not os.path.exists(self.data_directory):
            os.makedirs(self.data_directory)
        
        logger.debug("Data directory: " + self.data_directory)
        
        self.last_day = time.localtime().tm_mday
        
        self.data = []
        
        self._initialized = True
        
        # Setup the link to todays data
        self.setup_data_file()
        
    def isInitialized(self):
        return self._initialized
    
    def setup_data_file(self):
        if not self._initialized:
            logger.error( "setup_data_file called before _initialized." )
            return
        
        today = datetime.date.today().strftime( self.archive_prefix + '_%Y_%m_%d.csv' )
        todays_filename = self.data_directory + "/" + today
        
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
    
        # Clear the current data
        self.data = []
        
        # Open the link as a data file
        try:
            # Open the data file
            self.file_handle = open(self.filename, 'a+')
        except:
            logger.error( "Failed to open "+ self.filename +" : " + repr(sys.exc_info()[1]) )
            self._initialized = False
            return
            
        # Load the data from file (only happens when a file already existed for today)
        for line in self.file_handle.readlines():
            line_data = line.rstrip().split(',')
            
            dt = datetime.datetime.fromtimestamp(float(line_data[0]))
            year   = dt.strftime('%Y')
            month  = str(int(dt.strftime('%m')) - 1) # javascript expects month in 0-11, strftime gives 1-12 
            day    = dt.strftime('%d')
            hour   = dt.strftime('%H')
            minute = dt.strftime('%M')
            second = dt.strftime('%S')
            time_str = 'new Date(%s,%s,%s,%s,%s,%s)' % (year,month,day,hour,minute,second)
            
            self.data.append( {'time_str':time_str, 'data':line_data[1:]} )
        
    
    def add_data(self, data): # data should be an array of strings
        
        if not self._initialized:
            logger.error( "add_data called before _initialized." )
            return
        
        if not isinstance(data, list):
            logger.error( "add_data called with non-list data" )
            return
        
        if len( data ) < 1:
            return
        
        #logger.debug( "caller: " + os.path.basename(inspect.stack()[1][1]) + " gave me: " + str( data ) )
        
        self.mutex.acquire()
        
        # Check if file needs to be changed
        now = time.time()
        if time.localtime(now).tm_mday != self.last_day:
            self.last_day = time.localtime(now).tm_mday
            self.setup_data_file()
        
        # Build the data string
        result = str(now)
        for item in data:
            result += "," + item
    
        # Write to the file
        self.file_handle.write(result)
        self.file_handle.write("\n")
        self.file_handle.flush()
        
        # Compute the javascript time string (probably not the best place for this)
        dt = datetime.datetime.fromtimestamp(now)
        year   = dt.strftime('%Y')
        month  = str(int(dt.strftime('%m')) - 1) # javascript expects month in 0-11, strftime gives 1-12 
        day    = dt.strftime('%d')
        hour   = dt.strftime('%H')
        minute = dt.strftime('%M')
        second = dt.strftime('%S')
        time_str = 'new Date(%s,%s,%s,%s,%s,%s)' % (year,month,day,hour,minute,second)
    
        #                      time string      string list
        self.data.append({'time_str':time_str, 'data':data})
        
        self.mutex.release()
    

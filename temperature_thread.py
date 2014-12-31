import csv
import os
import subprocess
import sys
import time
import datetime
from threading import Thread, Lock


#
# Example usage:
#
#  t1 = temperature_thread.Temperature_Thread(filename = "main_floor_temps.csv", 
#                                             device_name = ["main_floor_temp"])
#  if t1 != None:
#    t1.start()
#

class Temperature_Thread(Thread):
    def __init__(self, config):
        Thread.__init__(self)
        self.initialized = False
        self.mutex = Lock()
        self.run_lock = Lock()
        self.running = False
        self.current_temps = {}
        config_sec = "temperature_thread"

        if config_sec not in config.sections():
            print config_sec + " section missing from config file"
            return

        if "data_file" not in config.options(config_sec):
            print "data_file property missing from " + config_sec + " section"
            return
        
        if "device_names" not in config.options(config_sec):
            print "device_names property missing from " + config_sec + " section"
            return

        self.filename = config.get(config_sec, "data_file")
        self.device_names = config.get(config_sec, "device_names").split(',')

        for device in self.device_names:
             self.current_temps[device] = 0.0
        self.current_average_temperature = 0.0

        try:
            self.file_handle = open(self.filename, 'a+')
            self.file_handle.seek(0,2)
        except:
            print "Failed to open", self.filename, ":", sys.exc_info()[1]
            return
        
        self.initialized = True
    
    def isInitialized(self):
        return self.initialized
    
    def run(self):
        
        if not self.initialized:
            print "Warning: Temperature_Thread started before initialized, not running."
            return
        
        self.running = self.run_lock.acquire()
        while self.running:
          
            t = {}
            x = 0.0
            count = 0
            for device in self.device_names:
              
                t[device] = subprocess.Popen(["spark","get",device,"temperature"], stdout=subprocess.PIPE).stdout.read().strip()
              
                try:
                    x = x + float(t[device])
                    self.current_temps[device] = float(t[device])
                    count = count + 1
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    print "Error getting temperature ("+device+"), got: \"" + t[device] + "\" setting to null"
                    t[device] = "null"
          
            if count > 0:
                self.current_average_temperature = x / count
          
            self.mutex.acquire()
            self.file_handle.write(str(time.time()))
            for device in self.device_names:
                self.file_handle.write("," + t[device])
            self.file_handle.write("\n")
            self.file_handle.flush()
            self.mutex.release()
            
            for i in range(120):
                if self.running:
                    time.sleep(1)
        
        self.run_lock.release()
  
    def stop(self):
        self.running = False
        self.run_lock.acquire() # Wait for the thread to stop
        self.file_handle.close()
    
    def get_average_temp(self):
        return self.current_average_temperature
    
    def get_current_device_temp(self, device):
        if device in self.current_temps:
            return self.current_temps[device]
        print "WARNING:",device,"not found" 
        return 0.0
    
    def get_history(self, days=1, seconds=0):
        
        # start_time is "now" minus days and seconds
        # only this much data will be shown
        start_time = datetime.datetime.now() - datetime.timedelta(days,seconds)
        
        # Load the data from the file
        self.mutex.acquire()
        file_handle = open(self.filename, 'r')
        csvreader = csv.reader(file_handle)
        tempdata = []
        try:
            for row in csvreader:
                tempdata.append(row)
        except csv.Error, e:
            print 'ERROR: file %s, line %d: %s' % (self.filename, csvreader.line_num, e)
        self.mutex.release()
        
        # Build the return string
        return_string = ""
        for i, row in enumerate(tempdata):
            
            # Skip the ones before the start_time
            dt = datetime.datetime.fromtimestamp(float(row[0]))
            if dt < start_time:
                continue
            
            time = dt.strftime('%I:%M:%S %p')
            temp1 = row[1]
            temp2 = row[2]
            temp3 = row[3]
            
            return_string += ("        ['%s',  %s, %s, %s],\n" % (time,temp1,temp2,temp3))
        
        if len(return_string) > 2:
            return_string = return_string[:-2]
        
        return return_string
            
            
            
            
            
            
            
            
            
            
            
            
            
            

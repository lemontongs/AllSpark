import csv
import os
import subprocess
import sys
import time
import datetime
import psutil
from threading import Thread, Lock


#
# Example usage:
#
#  t1 = temperature_thread.Memory_Thread(filename = "main_floor_temps.csv")
#  if t1.isInitialized():
#    t1.start()
#

class Memory_Thread(Thread):
    def __init__(self, filename, collect_period = 60):
        Thread.__init__(self)
        self.mutex = Lock()
        self.running = False
        self.initialized = False
        self.filename = filename
        self.collect_period = collect_period
        
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
            print "Warning: Memory_Thread started before initialized, not running."
            return
        
        self.running = True
        while self.running:
          
          self.mutex.acquire()
          self.file_handle.write(str(time.time()) + "," + str(psutil.phymem_usage().percent) + "\n")
          self.file_handle.flush()
          self.mutex.release()
          
          time.sleep(self.collect_period)
  
    def stop(self):
        self.running = False
        self.file_handle.close()
    
    def get_history(self, days=1, seconds=0):
        
        # start_time is "now" minus days and seconds
        # only this much data will be shown
        start_time = datetime.datetime.now() - datetime.timedelta(days,seconds)
        
        # Load the data from the file
        self.mutex.acquire()
        file_handle = open(self.filename, 'r')
        csvreader = csv.reader(file_handle)
        memdata = []
        try:
            for row in csvreader:
                memdata.append(row)
        except csv.Error, e:
            print 'ERROR: file %s, line %d: %s' % (self.filename, csvreader.line_num, e)
        self.mutex.release()
        
        # Build the return string
        return_string = ""
        for i, row in enumerate(memdata):
            
            # Skip the ones before the start_time
            dt = datetime.datetime.fromtimestamp(float(row[0]))
            if dt < start_time:
                continue
            
            time = dt.strftime('%I:%M:%S %p')
            mem = row[1]
            
            return_string += ("        ['%s',  %s],\n" % (time,mem))
        
        if len(return_string) > 2:
            return_string = return_string[:-2]
        
        return return_string
            
            
if __name__ == "__main__":
    
    mem = Memory_Thread(filename = "mem_usage.csv", collect_period = 2)
    
    if not mem.isInitialized():
        print "ERROR: initialization failed"
        os._exit(0)
    
    mem.start()
    
    print "Collecting data (1 minute)..."
    time.sleep(60)
    
    print mem.get_history()
    
    mem.stop()

            
            
            
            
            
            
            
            
            
            
            
            

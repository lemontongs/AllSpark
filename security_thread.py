import csv
import os
import subprocess
import sys
import time
import datetime
import psutil
from threading import Thread, Lock



class Security_Thread(Thread):
    def __init__(self, config, spark_if):
        Thread.__init__(self)
        self.initialized = False
        self.mutex = Lock()
        self.running = False
        config_sec = "security_thread"

        self.spark = spark_if

        if config_sec not in config.sections():
            print config_sec + " section missing from config file"
            return

        if "monitor_device_name" not in config.options(config_sec):
            print "monitor_device_name property missing from " + config_sec + " section"
            return

        self.monitor_device_name = config.get(config_sec, "monitor_device_name")

        if "num_zones" not in config.options(config_sec):
            print "num_zones property missing from " + config_sec + " section"
            return

        self.num_zones = int(config.get(config_sec, "num_zones"))
        self.zones = []
        
        for zone in range(self.num_zones):
            zone_index = "zone_"+str(zone)
            
            if zone_index not in config.options(config_sec):
                print zone_index+" property missing from " + config_sec + " section"
                return
                
            self.zones.append(config.get(config_sec, zone_index))

        print self.zones

        if "collect_period" not in config.options(config_sec):
            self.collect_period = 5
        else:
            self.collect_period = float(config.get(config_sec, "collect_period", True))
        
#        try:
#            self.file_handle = open(self.filename, 'a+')
#            self.file_handle.seek(0,2)
#        except:
#            print "Failed to open", self.filename, ":", sys.exc_info()[1]
#            return
        
        self.sensor_states = ""
        
        
        self.initialized = True
    
    def isInitialized(self):
        return self.initialized
    
    def getSensorStates(self):
        self.mutex.acquire()
        ss = self.sensor_states
        self.mutex.release()
        return ss
    
    def run(self):
        
        if not self.initialized:
            print "Warning: Security_Thread started before initialized, not running."
            return
        
        self.running = True
        while self.running:
          
          self.mutex.acquire()
          self.sensor_states = ""
          for zone in range(self.num_zones):
              zone_index = "zone_"+str(zone)
              state = self.spark.callNamedDeviceFunction( self.monitor_device_name, "digitalread", "D"+str(zone), "return_value")
              self.sensor_states = self.sensor_states + "<br>"+self.zones[zone]+": "+str(state)
          self.mutex.release()
          
          time.sleep(self.collect_period)
  
    def stop(self):
        self.running = False
    
            
            
if __name__ == "__main__":
    
    sec = Security_Thread()
    
    if not sec.isInitialized():
        print "ERROR: initialization failed"
        os._exit(0)
    
    sec.start()
    
    print "Collecting data (1 minute)..."
    time.sleep(60)
    
    print sec.get_history()
    
    sec.stop()

            
            
            
            
            
            
            
            
            
            
            
            

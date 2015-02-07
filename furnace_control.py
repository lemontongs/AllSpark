#! /usr/bin/env python

import ConfigParser
import sys
import time
from threading import Thread, Lock
import os
import RPi.GPIO as GPIO

import utilities

GPIO.setwarnings(False)

class Furnace_Control(Thread):
    def __init__(self, zones, set_point_filename, furnace_state_filename): # example zones:  [ {'name':'top', 'pin':18, 'get_temp':get_temp} ]
        Thread.__init__(self)
        
        self.initialized = False
        self.zones = zones
        
        if os.geteuid() != 0:
            print "ERROR: Running in non-privaleged mode, Furnace_Control not running" 
            return
        
        if len(zones) == 0:
            print "Warning: no zones defined"
            return
        
        self.set_point_config = ConfigParser.ConfigParser()
        
        # Create the set point file if it does not yet exist
        self.set_point_filename = set_point_filename
        self.set_point_section = 'set_points'
        if not os.path.exists(self.set_point_filename):
            self.set_point_config.add_section(self.set_point_section)
        else:
            self.set_point_config.read(self.set_point_filename)
        
        # Verify the set points. This will create them if they dont exist in the config section
        self.verify_set_points()
        
        # Setup the GPIO
        try:
            GPIO.setmode(GPIO.BCM)
            for i, zone in enumerate(self.zones):
                GPIO.setup(zone['pin'],GPIO.OUT)
                self.off(zone['pin'])
        except:
            print sys.exc_info()
            GPIO.cleanup()
            return
        
        # Open the furnace state file
        self.mutex = Lock()
        self.furnace_state_filename = furnace_state_filename
        try:
            self.furnace_state_file = open(self.furnace_state_filename, 'a+')
            self.furnace_state_file.seek(0,2)
        except:
            print "Failed to open", self.furnace_state_file, ":", sys.exc_info()[1]
            return
        
        self.running = False
        self.initialized = True

    def isInitialized(self):
        return self.initialized
    
    def verify_set_points(self):
        for zone in self.zones:
            if not self.set_point_config.has_option(self.set_point_section, zone['name']):
                self.set_point_config.set(self.set_point_section, zone['name'], "70.0")
            
            t = float(self.set_point_config.get(self.set_point_section, zone['name'], True))
            if 50 > t or t > 90:
                print "WARNING: set point for '" + zone['name'] + "' is out of bounds (<50 or >90). Got: " + str(t) + ". Setting it to 70.0"
                self.set_point_config.set(self.set_point_section, zone['name'], "70.0")
        
        with open(self.set_point_filename, 'wb') as configfile:
            self.set_point_config.write(configfile)
    
    def stop(self):
        if self.initialized:
            self.initialized = False
            self.running = False
            time.sleep(2)
            for i, zone in enumerate(self.zones):
                self.off(zone['pin'])
            GPIO.cleanup()
            self.mutex.acquire()
            self.furnace_state_file.close()
            self.mutex.release()

    def on(self, pin):
        if self.initialized:
            GPIO.output(pin,False)

    def off(self, pin):
        if self.initialized:
            GPIO.output(pin,True)

    def get_set_point(self, zone_name):
        found = False
        for i, zone in enumerate(self.zones):
            if zone['name'] == zone_name:
                found = True
                v = self.set_point_config.get(self.set_point_section, zone['name'], True)
                return float(v)
        if not found:
             print "Warning:", zone_name, "not found"
        return 60.0

    def parse_set_point_message(self, msg):
        if len(msg.split(',')) != 3:
            print "Error parsing set_point message"
            return
        
        self.set_point(msg.split(',')[1], float(msg.split(',')[2]))

    def set_point(self, zone_name, set_point):
        found = False
        for i, zone in enumerate(self.zones):
            if zone['name'] == zone_name:
                found = True
                self.set_point_config.set(self.set_point_section, zone['name'], float(set_point))
                self.verify_set_points()
        if not found:
            print "Warning: zone not found"

    def run(self):
        
        if not self.initialized:
            print "Warning: started before initialized, not running"
            return
        
        f = open("logs/furnace_log","a")

        self.running = True
        while self.running:
            
            self.mutex.acquire()
            self.furnace_state_file.write(str(time.time()))
            
            for i, zone in enumerate(self.zones):
                temp = zone['get_temp']()
                
                if temp == 0.0:
                    continue
                
                set_p = self.get_set_point(zone['name'])
                
                s = ""
                if temp < set_p:
                    s = s + "heating"
                    self.furnace_state_file.write(","+zone['name'])
                    self.on(zone['pin'])
                if temp > set_p:
                    s = s + "cooling"
                    self.off(zone['pin'])
                
                
                f.write("Current: "+str(temp)+" "+s+" set_point: "+str(set_p)+"\n")
                f.flush()
                
            self.furnace_state_file.write("\n")
            self.furnace_state_file.flush()
            self.mutex.release()
            time.sleep(60)
        f.close()
    
    def get_history(self, days=1, seconds=0):
        search_items = [ z['name'] for z in self.zones ]
        return utilities.convert_file_to_timeline_string(self.furnace_state_filename, self.mutex, search_items, days=days, seconds=seconds)
#
# MAIN
#
if __name__ == "__main__":
    
    temp = 80.0
    modifier = 1.0
        
    def get_temp():
        global temp, modifier
        if temp > 80 or temp < 70:
            modifier = -modifier
        temp = temp + modifier
        return temp
    
    zones = [ {'name':'top',     'pin':18, 'get_temp':get_temp},
              {'name':'main',    'pin':23, 'get_temp':get_temp},
              {'name':'basement','pin':24, 'get_temp':get_temp} ]

    fc = Furnace_Control(zones)
    
    fc.on(zones[0]['pin'])
    
    time.sleep(2)

    fc.off(zones[0]['pin'])
    
    fc.set_point(zones[0]['name'], 75.0)
    
    fc.start()

    time.sleep(20)
    
    fc.stop()


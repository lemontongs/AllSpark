#! /usr/bin/env python

import sys
import time
from threading import Thread, Lock
import os
import RPi.GPIO as GPIO

GPIO.setwarnings(False)

class Furnace_Control(Thread):
    def __init__(self, zones): # example zones:  [ {'name':'top', 'pin':18, 'get_temp':get_temp} ]
        Thread.__init__(self)
        
        self.initialized = False
        self.zones = zones
        
        if os.geteuid() != 0:
            print "ERROR: Running in non-privaleged mode, Furnace_Control not running" 
            return
        
        if len(zones) == 0:
            print "Warning: no zones defined"
            return
        
        try:
            GPIO.setmode(GPIO.BCM)
            for i, zone in enumerate(self.zones):
                GPIO.setup(zone['pin'],GPIO.OUT)
                self.off(zone['pin'])
                self.zones[i]['set_point'] = zone['get_temp']()
        except:
            print sys.exc_info()
            GPIO.cleanup()
            return
        
        self.running = False
        self.initialized = True

    def isInitialized(self):
        return self.initialized

    def stop(self):
        if self.initialized:
            self.initialized = False
            self.running = False
            time.sleep(2)
            for i, zone in enumerate(self.zones):
                self.off(zone['pin'])
            GPIO.cleanup()

    def on(self, pin):
        if self.initialized:
            GPIO.output(pin,True)

    def off(self, pin):
        if self.initialized:
            GPIO.output(pin,False)

    def get_set_point(self, zone_name):
        found = False
        for i, zone in enumerate(self.zones):
            if zone['name'] == zone_name:
                found = True
                return zone['set_point']
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
                self.zones[i]['set_point'] = set_point
        if not found:
            print "Warning: zone not found"

    def run(self):
        
        if not self.initialized:
            print "Warning: started before initialized, not running"
            return
        
        f = open("logs/furnace_log","a")

        self.running = True
        while self.running:
            for i, zone in enumerate(self.zones):
                temp = zone['get_temp']()
                
                if temp == 0.0:
                    continue
                
                s = ""
                if temp < zone['set_point']:
                    s = s + "heating"
                    self.on(zone['pin'])
                if temp > zone['set_point']:
                    s = s + "cooling"
                    self.off(zone['pin'])
            
                f.write("Current: "+str(temp)+" "+s+" set_point: "+str(zone['set_point'])+"\n")
                f.flush()
            time.sleep(60)
        f.close()

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


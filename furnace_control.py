#! /usr/bin/env python

import sys
import time
from threading import Thread, Lock
import os
import RPi.GPIO as GPIO


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

    def close(self):
        if self.initialized:
            self.initialized = False
            self.running = False
            GPIO.cleanup()

    def on(self, pin):
        if self.initialized:
            GPIO.output(pin,True)

    def off(self, pin):
        if self.initialized:
            GPIO.output(pin,False)

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
        
        self.running = True
        while self.running:
            temp = self.zones[0]['get_temp']()
            s = ""
            if temp < self.zones[0]['set_point']:
                s = s + "heating"
            if temp > self.zones[0]['set_point']:
                s = s + "cooling"
            
            print "Current:", temp, s, "set_point:", self.zones[0]['set_point']
            time.sleep(0.5)

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
    
    zones = [ {'name':'top',  'pin':18, 'get_temp':get_temp} ]

    fc = Furnace_Control(zones)
    
    fc.on(zones[0]['pin'])
    
    time.sleep(2)

    fc.off(zones[0]['pin'])
    
    fc.set_point(zones[0]['name'], 75.0)
    
    fc.start()

    time.sleep(20)
    
    fc.close()


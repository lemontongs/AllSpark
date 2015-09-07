#! /usr/bin/env python

import ConfigParser
import sys
import time
from threading import Thread, Lock
import os
import imp
import file_utilities

try:
    imp.find_module('RPi')
    import RPi.GPIO as GPIO
    GPIO.setwarnings(False)
    USING_RPI_GPIO = True
except ImportError:
    USING_RPI_GPIO = False
    from utilities import GPIO
    print "Warning: using local GPIO module"



class Furnace_Control(Thread):
    def __init__(self, object_group, set_point_filename, furnace_state_filename):
        Thread.__init__(self)
        self.og = object_group
        self.initialized = False
        self.set_point_lock = Lock()
        
        
        if USING_RPI_GPIO and (os.geteuid() != 0):
            print "ERROR: Running in non-privaleged mode, Furnace_Control not running" 
            return
        
        # Create the set point file if it does not yet exist
        self.set_point_config = ConfigParser.ConfigParser()
        self.set_point_filename = set_point_filename
        self.set_point_section = 'set_points'
        self.ctrl_pins_section = 'control_pins'
        self.user_rule_section = 'rules'
        
        # Load and verify the set point file.
        self.load_set_point_file()
        
        # Setup the GPIO
        try:
            GPIO.setmode(GPIO.BCM)
            for zone in self.zones:
                GPIO.setup(self.zones[zone]['pin'], GPIO.OUT)
                self.off(self.zones[zone]['pin'])
        except:
            print "Error: furnace_control: init: " + repr(sys.exc_info())
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
    
    def load_set_point_file(self):
        
        # If the file does not exist, create it
        if not os.path.exists(self.set_point_filename):
            self.set_point_config.add_section(self.set_point_section)
            self.set_point_config.add_section(self.ctrl_pins_section)
            self.set_point_config.add_section(self.user_rule_section)
            
            for device in self.og.thermostat.getDeviceNames():
                self.set_point_config.set(self.set_point_section, device, "65.0")
                self.set_point_config.set(self.ctrl_pins_section, device, "None")
            
        else:
            self.set_point_config.read(self.set_point_filename)
            
            if not self.set_point_config.has_section(self.set_point_section):
                self.set_point_config.add_section(self.set_point_section)
            
            if not self.set_point_config.has_section(self.ctrl_pins_section):
                self.set_point_config.add_section(self.ctrl_pins_section)
            
            for device in self.og.thermostat.getDeviceNames():
            
                if not self.set_point_config.has_option(self.set_point_section, device):
                    self.set_point_config.set(self.set_point_section, device, "65.0")
                
                if not self.set_point_config.has_option(self.ctrl_pins_section, device):
                    self.set_point_config.set(self.set_point_section, device, "None")
                
        # verify the contents of the file, and create the zones structure
        self.zones = {}
        for device in self.og.thermostat.getDeviceNames():
            
            t = 65.0
            try:
                t = float(self.set_point_config.get(self.set_point_section, device, True))
            except:
                pass
            
            if 50 > t or t > 90:
                print "WARNING: set point for '" + device + "' is out of bounds (<50 or >90). Got: " + str(t) + ". Setting it to 65.0"
                t = 65.0
            
            self.zones[device] = {'set_point':t}
            self.set_point_config.set(self.set_point_section, device, t)
            
            p = None
            try:
                p = self.set_point_config.get(self.ctrl_pins_section, device, True)
                if "None" in p:
                    print "WARNING: pin for '" + device + "' not set"
                    p = None
                    
                p = int(p)
            except:
                print "WARNING: pin for '" + device + "' invalid"
            
            self.zones[device]['pin'] = p
        
        # Write the file, with the corrections (if any)
        self.save_zones_to_file()
        
        # Load the rules
        self.rules = {'away_set_point' : 60.0, 'rules' : {} }
        
        for option in self.set_point_config.options(self.user_rule_section):
            if 'away_set_point' in option:
                try:
                    self.rules['away_set_point'] = \
                        float(self.set_point_config.get(self.user_rule_section, 'away_set_point', True))
                except:
                    pass
            else:
                self.rules['rules'][option] = \
                    self.set_point_config.get(self.user_rule_section, option, True)
        
    
    def save_zones_to_file(self):
        for device in self.zones.keys():
            set_point = str(self.zones[device]['set_point'])
            self.set_point_config.set(self.set_point_section, device, set_point)
        
        with open(self.set_point_filename, 'wb') as configfile:
            self.set_point_config.write(configfile)

        
    def stop(self):
        if self.initialized:
            self.initialized = False
            self.running = False
            time.sleep(2)
            for zone in self.zones:
                self.off(self.zones[zone]['pin'])
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
    
    
    # Get the set point, this can be different if the user is not home
    def get_set_point(self, zone_name):
        if self.initialized:
            
            self.set_point_lock.acquire()
            
            if zone_name not in self.zones.keys():
                print "Warning: get_set_point:", zone_name, "not found"
                return 60.0
            
            set_point = self.rules['away_set_point']
            
            # if any of the users are home AND have this zone in there list, 
            # use the custom set point (from the set point file)
            for user in self.rules['rules']:
                if self.og.user_thread.is_user_home(user) and (zone_name in self.rules['rules'][user]):
                    set_point = self.zones[zone_name]['set_point']
                    break
            
            # None of the users who are home have this zone in there rules so 
            # use the "away" set point
            self.set_point_lock.release()
            return set_point
        
    def parse_set_point_message(self, msg):
        if len(msg.split(',')) != 3:
            print "Error parsing set_point message"
            return
        
        zone = msg.split(',')[1]
        
        self.set_point_lock.acquire()
        try:
            if zone not in self.zones.keys():
                print "Error parsing set_point message: "+zone+" not found"
                self.set_point_lock.release()
                return
                
            set_point = 65.0
            try:
                set_point = float(msg.split(',')[2])
            except:
                pass
            
            self.zones[zone]['set_point'] = set_point
            self.save_zones_to_file()
        except:
            self.set_point_lock.release()
            raise

        self.set_point_lock.release()

    def run(self):
        
        if not self.initialized:
            print "Warning: started before initialized, not running"
            return
        
        f = open("logs/furnace_log","a")

        self.running = True
        while self.running:
            
            self.mutex.acquire()
            self.furnace_state_file.write(str(time.time()))
            
            f.write("###########################\n")
            f.write("# Zone # Temp # Set Point #\n")
            
            for zone in self.zones:
                
                temp = self.og.thermostat.get_current_device_temp(zone)
                pin = self.zones[zone]['pin']
                set_p = self.get_set_point(zone)
                
                s = ""
                if temp == -1000.0:
                    s = "invalid"
                    self.off(pin)
                elif temp < set_p:
                    s = "heating"
                    self.furnace_state_file.write(","+zone)
                    self.on(pin)
                elif temp > set_p + 1.0:
                    s = "cooling"
                    self.off(pin)
                
                f.write(zone+" "+str(temp)+" "+str(set_p)+" "+s+"\n")
                
            f.flush()
            
            self.furnace_state_file.write("\n")
            self.furnace_state_file.flush()
            self.mutex.release()
            time.sleep(60)
        f.close()
    
    def get_history(self, days=1, seconds=0):
        search_items = self.zones.keys()
        return file_utilities.convert_file_to_timeline_string(self.furnace_state_filename, self.mutex, search_items, days=days, seconds=seconds)
#
# MAIN
#
if __name__ == "__main__":
    
    #TODO: fix this!
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

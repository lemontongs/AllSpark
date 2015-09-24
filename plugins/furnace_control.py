#! /usr/bin/env python

import sys
import time
from threading import Thread
import os
import imp
import logging
from utilities import data_logger
from utilities import config_utils

CONFIG_SEC_NAME = "furnace_control"

logger = logging.getLogger('allspark.' + CONFIG_SEC_NAME)

try:
    imp.find_module('RPi')
    import RPi.GPIO as GPIO
    GPIO.setwarnings(False)
    USING_RPI_GPIO = True
except ImportError:
    USING_RPI_GPIO = False
    from utilities import GPIO
    logger.info("Using local GPIO module")


class Furnace_Control(Thread):
    def __init__(self, object_group, config):
        Thread.__init__(self, name=CONFIG_SEC_NAME)
        self.og = object_group
        self.initialized = False
        
        if USING_RPI_GPIO and (os.geteuid() != 0):
            logger.info("Running in non-privaleged mode, Furnace_Control not running") 
            return
        
        # Get parameters from the config file

        if not config_utils.check_config_section( config, CONFIG_SEC_NAME ):
            return

        self.filename = config_utils.get_config_param( config, CONFIG_SEC_NAME, "data_file")
        if self.filename == None:
            return

        data_directory = config_utils.get_config_param( config, CONFIG_SEC_NAME, "data_directory")
        if data_directory == None:
            return
        
        # Get the device pins from the config file
        self.zones = self.og.thermostat.getDeviceNames()
        self.pins = {}
        for device in self.zones:
            pin_str = config_utils.get_config_param( config, CONFIG_SEC_NAME, device)
            if pin_str == None:
                return
            self.pins[device] = int(pin_str)
        
        
        # Setup the GPIO
        try:
            GPIO.setmode(GPIO.BCM)
            for zone in self.zones:
                GPIO.setup(self.pins[zone], GPIO.OUT)
                self.off(self.pins[zone])
        except:
            logger.error("Error: furnace_control: init: " + repr(sys.exc_info()))
            GPIO.cleanup()
            return
        
        
        # Setup data logger
        self.data_logger = data_logger.Data_Logger( data_directory, self.filename, "furnace", self.zones ) 
        
        self.running = False
        self.initialized = True

    @staticmethod
    def get_template_config(config):
        config.add_section(CONFIG_SEC_NAME)
        config.set(CONFIG_SEC_NAME,"temp_data_dir", "data")
        config.set(CONFIG_SEC_NAME,"data_directory", "%(temp_data_dir)s/furnace_data")
        config.set(CONFIG_SEC_NAME, "data_file", "%(data_directory)s/today.csv")
        config.set(CONFIG_SEC_NAME, "<Particle device name for Zone_1>", "<pin for zone 1>")
        config.set(CONFIG_SEC_NAME, "<Particle device name for Zone_2>", "<pin for zone 2>")
        config.set(CONFIG_SEC_NAME, "<Particle device name for Zone_3>", "<pin for zone 3>")
        
    def isInitialized(self):
        return self.initialized
    
    def stop(self):
        if self.initialized:
            self.initialized = False
            self.running = False
            time.sleep(2)
            for zone in self.zones:
                self.off(self.pins[zone])
            GPIO.cleanup()
            

    def on(self, pin):
        if self.initialized:
            GPIO.output(pin,False)

    def off(self, pin):
        if self.initialized:
            GPIO.output(pin,True)
    
    def run(self):
        
        logger.info( "Thread started" )
        
        if not self.initialized:
            logger.error( "Furnace_Control: Started before initialized, not running" )
            return
        
        f = open("logs/furnace_log","a")

        self.running = True
        while self.running:
            
            logger.info( "Thread executing" )
        
            f.write("#\n")
            
            zones_that_are_heating = []
            
            for zone in self.zones:
                
                temp = self.og.thermostat.get_current_device_temp(zone)
                pin = self.pins[zone]
                set_p = self.og.set_point.get_set_point(zone)
                
                s = ""
                if temp == -1000.0:
                    s = "invalid"
                    self.off(pin)
                elif temp < set_p:
                    s = "heating"
                    zones_that_are_heating.append( zone )
                    self.on(pin)
                elif temp > set_p + 1.0:
                    s = "cooling"
                    self.off(pin)
                
                f.write("Z: "+zone+" T: "+str(temp)+" SP: "+str(set_p)+" "+s+"\n")
                
            self.data_logger.add_data( zones_that_are_heating )
            
            f.flush()
            
            for _ in range(60):
                if self.running:
                    time.sleep(1)
            
        f.close()
        
        logger.info( "Thread stopped" )
        
    
    def get_html(self):
        html = """
        
        <div id="furnace" class="jumbotron">
            <div class="row">
                <h2>Furnace State:</h2>
                <div class="col-md-12">
                    <div id="furnace_chart_div"></div>
                </div>
            </div>
        </div>
        
        """
        
        return html
    
    def get_javascript(self):
        jscript = """
            function drawFurnaceData()
            {
                var dataTable = new google.visualization.DataTable();

                dataTable.addColumn({ type: 'string', id: 'Zone' });
                dataTable.addColumn({ type: 'date', id: 'Start' });
                dataTable.addColumn({ type: 'date', id: 'End' });

                dataTable.addRows([
                  
                %s             //   FURNACE IS ON DATA

                ]);

                chart = new google.visualization.Timeline(document.getElementById('furnace_chart_div'));
                chart.draw(dataTable);
            }
            ready_function_array.push( drawFurnaceData )
            
        """ % self.data_logger.get_google_chart_string()
        
        return jscript
    
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


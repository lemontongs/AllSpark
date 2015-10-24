#! /usr/bin/env python

import sys
import time
import logging
import traceback
from utilities.data_logging import presence_logger
from utilities import config_utils
from utilities import udp_interface
from utilities import thread_base

CONFIG_SEC_NAME = "furnace_control"

logger = logging.getLogger('allspark.' + CONFIG_SEC_NAME)


class Furnace_Control(thread_base.AS_Thread):
    def __init__(self, object_group, config):
        thread_base.AS_Thread.__init__(self, CONFIG_SEC_NAME)
        
        self.og = object_group
        
        # Get parameters from the config file

        if not config_utils.check_config_section( config, CONFIG_SEC_NAME ):
            return

        data_directory = config_utils.get_config_param( config, CONFIG_SEC_NAME, "data_directory")
        if data_directory == None:
            return
        
        address = config_utils.get_config_param( config, CONFIG_SEC_NAME, "address")
        if address == None:
            return
        
        port = config_utils.get_config_param( config, CONFIG_SEC_NAME, "port")
        if port == None:
            return
        
        # Get the device pins from the config file
        self.zones = self.og.thermostat.getDeviceNames()
        self.pins = {}
        for device in self.zones:
            pin_str = config_utils.get_config_param( config, CONFIG_SEC_NAME, device)
            if pin_str == None:
                return
            self.pins[device] = int(pin_str)
        
        # Furnace controller interface
        self.furnace_controller = udp_interface.UDP_Socket(address, port, CONFIG_SEC_NAME+"_interface")
        if not self.furnace_controller.isInitialized():
            logger.error( "Failed to initialize furnace_controller" )
            return
        
        # Setup data logger
        self.data_logger = presence_logger.Presence_Logger( data_directory, "furnace", self.zones ) 
        
        self._initialized = True

    @staticmethod
    def get_template_config(config):
        config.add_section(CONFIG_SEC_NAME)
        config.set(CONFIG_SEC_NAME,"temp_data_dir", "data")
        config.set(CONFIG_SEC_NAME,"data_directory", "%(temp_data_dir)s/furnace_data")
        config.set(CONFIG_SEC_NAME, "<Particle device name for Zone_1>", "<pin for zone 1>")
        config.set(CONFIG_SEC_NAME, "<Particle device name for Zone_2>", "<pin for zone 2>")
        config.set(CONFIG_SEC_NAME, "<Particle device name for Zone_3>", "<pin for zone 3>")
        
    def private_run_cleanup(self):
        if self.isInitialized():
            for zone in self.zones:
                self.off(self.pins[zone])
            self.furnace_controller.stop()

    def on(self, pin):
        if self.isInitialized():
            self.furnace_controller.send_message(str(pin)+"1")

    def off(self, pin):
        if self.isInitialized():
            self.furnace_controller.send_message(str(pin)+"0")
    
    def private_run(self):
            zones_that_are_heating = []
            
            try:
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
                    
                    logger.info("Z: "+zone+" T: "+str(temp)+" SP: "+str(set_p)+" "+s)
                    
                self.data_logger.add_data( zones_that_are_heating )
            
            except Exception as e:
                tb = "".join( traceback.format_tb(sys.exc_info()[2]) )
                self.logger.error( "exception occured in " + self.name + " thread: \n" + tb + "\n" + str( e ) ) 
                
            for _ in range(60):
                if self.isRunning():
                    time.sleep(1)
        
    
    def get_html(self):
        html = ""
        
        if self.isInitialized():
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
        jscript = ""
        
        if self.isInitialized():
            jscript = """
                function drawFurnaceData()
                {
                    %s
                }
                ready_function_array.push( drawFurnaceData )
                
            """ % self.data_logger.get_google_timeline_javascript("Zone","furnace_chart_div")
        
        return jscript
    
#
# MAIN
#
if __name__ == "__main__":
    import ConfigParser
    
    logging.getLogger('').handlers = []
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    format_str = '%(asctime)s %(name)-30s %(levelname)-8s %(message)s'
    console.setFormatter(logging.Formatter(format_str))
    logger.addHandler(console)
    
    #TODO: fix this!
    temp = 80.0
    modifier = 1.0
    
    def get_temp():
        global temp, modifier
        if temp > 80 or temp < 70:
            modifier = -modifier
        temp = temp + modifier
        return temp
    
    config = ConfigParser.ConfigParser()
    config.add_section(CONFIG_SEC_NAME)
    config.set(CONFIG_SEC_NAME, "data_file",      "test_data/today.csv")
    config.set(CONFIG_SEC_NAME, "data_directory", "test_data")
    config.set(CONFIG_SEC_NAME, "address",        "225.1.1.2")
    config.set(CONFIG_SEC_NAME, "port",           "5300")
    config.set(CONFIG_SEC_NAME, "top_floor_temp",     "3")
    config.set(CONFIG_SEC_NAME, "main_floor_temp",    "4")
    config.set(CONFIG_SEC_NAME, "basement_floor_temp","5")
    
    class subclass():
        def getDeviceNames(self):
            return ["top_floor_temp", "main_floor_temp", "basement_floor_temp"]
        def get_current_device_temp(self, zone):
            global temp, modifier
            if temp > 80 or temp < 70:
                modifier = -modifier
            temp = temp + modifier
            print temp
            return temp
        def get_set_point(self, zone):
            return 75
    class OG():
        def __init__(self):
            self.thermostat = subclass()
            self.set_point  = self.thermostat
    
    og = OG()
    
    fc = Furnace_Control(og, config)
    
    fc.on("3")
    time.sleep(1)
    fc.off("3")
    time.sleep(1)
    fc.on("3")
    fc.on("4")
    fc.on("5")
    time.sleep(1)
    
    fc.start()
    time.sleep(10)
    
    fc.on("3")
    fc.on("4")
    fc.on("5")
    time.sleep(1)
    fc.stop()


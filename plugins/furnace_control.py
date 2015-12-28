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


class FurnaceControl(thread_base.ASThread):
    def __init__(self, object_group, config):
        thread_base.ASThread.__init__(self, CONFIG_SEC_NAME)
        
        self.og = object_group
        
        # Get parameters from the config file

        if not config_utils.check_config_section( config, CONFIG_SEC_NAME ):
            return

        data_directory = config_utils.get_config_param( config, CONFIG_SEC_NAME, "data_directory")
        if data_directory is None:
            return
        
        address = config_utils.get_config_param( config, CONFIG_SEC_NAME, "address")
        if address is None:
            return
        
        command_port = config_utils.get_config_param( config, CONFIG_SEC_NAME, "command_port")
        if command_port is None:
            return
        
        response_port = config_utils.get_config_param( config, CONFIG_SEC_NAME, "response_port")
        if response_port is None:
            return
        
        # Get the device pins from the config file
        self.zones = self.og.thermostat.get_device_names()
        self.pins = {}
        for device in self.zones:
            pin_str = config_utils.get_config_param( config, CONFIG_SEC_NAME, device)
            if pin_str is None:
                return
            self.pins[device] = int(pin_str)
        
        # Furnace controller interface
        self.furnace_controller = udp_interface.UDPSocket(address,
                                                          response_port,
                                                          command_port,
                                                          CONFIG_SEC_NAME + "_inf")
        if not self.furnace_controller.is_initialized():
            logger.error( "Failed to initialize furnace_controller" )
            return
        self.furnace_controller.start()
        
        # Setup data logger
        self.data_logger = presence_logger.PresenceLogger(data_directory, "furnace", self.zones)

        self._initialized = True

    @staticmethod
    def get_template_config(config):
        config.add_section(CONFIG_SEC_NAME)
        config.set(CONFIG_SEC_NAME, "temp_data_dir", "data")
        config.set(CONFIG_SEC_NAME, "data_directory", "%(temp_data_dir)s/furnace_data")
        config.set(CONFIG_SEC_NAME, "<Particle device name for Zone_1>", "<pin for zone 1>")
        config.set(CONFIG_SEC_NAME, "<Particle device name for Zone_2>", "<pin for zone 2>")
        config.set(CONFIG_SEC_NAME, "<Particle device name for Zone_3>", "<pin for zone 3>")
        
    def private_run_cleanup(self):
        if self.is_initialized():
            for zone in self.zones:
                self.off(self.pins[zone])
            self.furnace_controller.stop()

    def on(self, pin):
        if self.is_initialized():
            self.furnace_controller.send_message(str(pin) + "1")

    def off(self, pin):
        if self.is_initialized():
            self.furnace_controller.send_message(str(pin) + "0")
    
    def private_run(self):
        
        # Send a heartbeat request
        logger.debug( "Sending heartbeat request to furnace controller" )
        self.furnace_controller.clear()
        self.furnace_controller.send_message( "00" )
        
        # Wait for the response
        response = self.furnace_controller.get(timeout = 5)
        if response is not None:
            (_, data) = response
            if data == "OK":
                logger.info( "Got heartbeat from furnace controller: " + data )
            else:
                logger.warning( "Got unexpected response from furnace controller: " + data )
                # TODO: reset the furnace controller 
        else:
            logger.warning( "Got no response from furnace controller" )
            # TODO: reset the furnace controller 
        
        zones_that_are_heating = []
        
        try:
            # For each zone
            for zone in self.zones:
                
                # Get the zones temp and set poin information
                current_temperature = self.og.thermostat.get_current_device_temp(zone)
                pin = self.pins[zone]
                set_p = self.og.set_point.get_set_point(zone)
                
                # Check the temp and turn the furnace on or off accordingly
                s = ""
                if current_temperature == -1000.0:
                    s = "invalid"
                    self.off(pin)
                elif current_temperature < set_p:
                    s = "heating"
                    zones_that_are_heating.append( zone )
                    self.on(pin)
                elif current_temperature > set_p + 1.0:
                    s = "cooling"
                    self.off(pin)
                
                logger.info("Z: " + zone + " T: " + str(current_temperature) + " SP: " + str(set_p) + " " + s)
            
            # Log the data
            self.data_logger.add_data( zones_that_are_heating )
        
        except Exception as e:
            tb = "".join( traceback.format_tb(sys.exc_info()[2]) )
            self.logger.error( "exception occurred in " + self.name + " thread: \n" + tb + "\n" + str( e ) )
            
        for _ in range(60):
            if self.is_running():
                time.sleep(1)

    def get_html(self):
        html = ""
        
        if self.is_initialized():
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
        
        if self.is_initialized():
            jscript = """
                function drawFurnaceData()
                {
                    %s
                }
                ready_function_array.push( drawFurnaceData )
                
            """ % self.data_logger.get_google_timeline_javascript("Furnace State", "Zone", "furnace_chart_div")
        
        return jscript
    
#
# MAIN
#
if __name__ == "__main__":
    import ConfigParser
    
    logging.getLogger('').handlers = []
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s %(name)-30s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
        
    conf = ConfigParser.ConfigParser()
    conf.add_section(CONFIG_SEC_NAME)
    conf.set(CONFIG_SEC_NAME, "data_directory", "test_data")
    conf.set(CONFIG_SEC_NAME, "address", "225.1.1.2")
    conf.set(CONFIG_SEC_NAME, "command_port", "5300")
    conf.set(CONFIG_SEC_NAME, "response_port", "5400")
    conf.set(CONFIG_SEC_NAME, "top_floor_temp", "3")
    conf.set(CONFIG_SEC_NAME, "main_floor_temp", "4")
    conf.set(CONFIG_SEC_NAME, "basement_floor_temp", "5")
    
    # TODO: fix this!
    temp = 80.0
    modifier = 1.0
    
    class Subclass:

        def __init__(self):
            pass

        @staticmethod
        def get_device_names():
            return ["top_floor_temp", "main_floor_temp", "basement_floor_temp"]

        @staticmethod
        def get_current_device_temp(_):
            global temp, modifier
            if temp > 80 or temp < 70:
                modifier = -modifier
            temp += modifier
            return temp

        @staticmethod
        def get_set_point(_):
            return 75


    class OG:
        def __init__(self):
            self.thermostat = Subclass()
            self.set_point = self.thermostat
    
    og = OG()
    
    fc = FurnaceControl(og, conf)
    
    if not fc.is_initialized():
        print "NOT INITIALIZED"
    
    else:
        fc.start()
        time.sleep(80)
        fc.stop()

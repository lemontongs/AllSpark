#! /usr/bin/env python

import sys
import time
import logging
import traceback
from utilities.data_logging import presence_logger
from utilities import config_utils
from utilities import udp_interface
from utilities.thread_base import ThreadedPlugin

PLUGIN_NAME = "furnace_control"


class FurnaceControlPlugin(ThreadedPlugin):

    @staticmethod
    def get_dependencies():
        return ['TemperatureMonitorPlugin', 'SetPointPlugin']

    def __init__(self, object_group, config):
        ThreadedPlugin.__init__(self, config=config, object_group=object_group, plugin_name=PLUGIN_NAME)

        # Get parameters from the config file

        if not self.enabled:
            return

        self.disable_commands = config_utils.get_config_param(config, PLUGIN_NAME, "disable_commands", self.logger)
        if self.disable_commands is None or self.disable_commands.lower() != "true":
            self.disable_commands = False
        else:
            self.disable_commands = True
            self.logger.warning("COMMANDS TO FURNACE CONTROLLER DISABLED")

        data_directory = config_utils.get_config_param(config, PLUGIN_NAME, "data_directory", self.logger)
        if data_directory is None:
            return

        address = config_utils.get_config_param(config, PLUGIN_NAME, "address", self.logger)
        if address is None:
            return
        
        command_port = config_utils.get_config_param(config, PLUGIN_NAME, "command_port", self.logger)
        if command_port is None:
            return
        
        response_port = config_utils.get_config_param(config, PLUGIN_NAME, "response_port", self.logger)
        if response_port is None:
            return
        
        # Get the device pins from the config file
        self.zones = self.og.thermostat_plugin.get_device_names()
        self.pins = {}
        for device in self.zones:
            pin_str = config_utils.get_config_param(config, PLUGIN_NAME, device, self.logger)
            if pin_str is None:
                return
            self.pins[device] = int(pin_str)
        
        # Furnace controller interface
        self.furnace_controller = udp_interface.UDPSocket(address,
                                                          response_port,
                                                          command_port,
                                                          PLUGIN_NAME + "_inf")
        if not self.furnace_controller.is_initialized():
            self.logger.error( "Failed to initialize furnace_controller" )
            return
        self.furnace_controller.start()
        
        # Setup data logger
        self.data_logger = presence_logger.PresenceLogger(data_directory, "furnace", self.zones)

        self._initialized = True

    @staticmethod
    def get_template_config(config):
        config.add_section(PLUGIN_NAME)
        config.set(PLUGIN_NAME, "temp_data_dir", "data")
        config.set(PLUGIN_NAME, "data_directory", "%(temp_data_dir)s/furnace_data")
        config.set(PLUGIN_NAME, "<Particle device name for Zone_1>", "<pin for zone 1>")
        config.set(PLUGIN_NAME, "<Particle device name for Zone_2>", "<pin for zone 2>")
        config.set(PLUGIN_NAME, "<Particle device name for Zone_3>", "<pin for zone 3>")
        
    def private_run_cleanup(self):
        if self.is_initialized():
            for zone in self.zones:
                self.off(self.pins[zone])
            self.furnace_controller.stop()

    def on(self, pin):
        if self.is_initialized() and not self.disable_commands:
            self.furnace_controller.send_message(str(pin) + "1")

    def off(self, pin):
        if self.is_initialized() and not self.disable_commands:
            self.furnace_controller.send_message(str(pin) + "0")
    
    def private_run(self):
        
        # Send a heartbeat request
        if not self.disable_commands:
            self.logger.debug( "Sending heartbeat request to furnace controller" )
            self.furnace_controller.clear()
            self.furnace_controller.send_message( "00" )
        
            # Wait for the response
            response = self.furnace_controller.get(timeout = 5)
            if response is not None:
                (_, data) = response
                if data == "OK":
                    self.logger.info( "Got heartbeat from furnace controller: " + data )
                else:
                    self.logger.warning( "Got unexpected response from furnace controller: " + data )
                    # TODO: reset the furnace controller
            else:
                self.logger.warning( "Got no response from furnace controller" )
                # TODO: reset the furnace controller
        
        zones_that_are_heating = []
        
        try:
            # For each zone
            for zone in self.zones:
                
                # Get the zones temp and set poin information
                current_temperature = self.og.thermostat_plugin.get_current_device_temp(zone)
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
                
                self.logger.info("Z: " + zone + " T: " + str(current_temperature) + " SP: " + str(set_p) + " " + s)
            
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
    conf.add_section(PLUGIN_NAME)
    conf.set(PLUGIN_NAME, "data_directory", "test_data")
    conf.set(PLUGIN_NAME, "address", "225.1.1.2")
    conf.set(PLUGIN_NAME, "command_port", "5300")
    conf.set(PLUGIN_NAME, "response_port", "5400")
    conf.set(PLUGIN_NAME, "top_floor_temp", "3")
    conf.set(PLUGIN_NAME, "main_floor_temp", "4")
    conf.set(PLUGIN_NAME, "basement_floor_temp", "5")
    
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
    
    fc = FurnaceControlPlugin(og, conf)
    
    if not fc.is_initialized():
        print "NOT INITIALIZED"
    
    else:
        fc.start()
        time.sleep(80)
        fc.stop()

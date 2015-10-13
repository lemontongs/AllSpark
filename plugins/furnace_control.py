#! /usr/bin/env python

import time
import logging
from utilities import data_logger
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

        self.filename = config_utils.get_config_param( config, CONFIG_SEC_NAME, "data_file")
        if self.filename == None:
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
        self.data_logger = data_logger.Data_Logger( data_directory, self.filename, "furnace", self.zones ) 
        
        self._initialized = True

    @staticmethod
    def get_template_config(config):
        config.add_section(CONFIG_SEC_NAME)
        config.set(CONFIG_SEC_NAME,"temp_data_dir", "data")
        config.set(CONFIG_SEC_NAME,"data_directory", "%(temp_data_dir)s/furnace_data")
        config.set(CONFIG_SEC_NAME, "data_file", "%(data_directory)s/today.csv")
        config.set(CONFIG_SEC_NAME, "<Particle device name for Zone_1>", "<pin for zone 1>")
        config.set(CONFIG_SEC_NAME, "<Particle device name for Zone_2>", "<pin for zone 2>")
        config.set(CONFIG_SEC_NAME, "<Particle device name for Zone_3>", "<pin for zone 3>")
        
    def private_run_cleanup(self):
        if self.isInitialized() and self.isRunning():
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
                
                logger.info("Z: "+zone+" T: "+str(temp)+" SP: "+str(set_p)+" "+s+"\n")
                
            self.data_logger.add_data( zones_that_are_heating )
            
            for _ in range(60):
                if self.isRunning():
                    time.sleep(1)
        
    
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
    
    zones = [ {'name':'top',     'pin':3, 'get_temp':get_temp},
              {'name':'main',    'pin':4, 'get_temp':get_temp},
              {'name':'basement','pin':5, 'get_temp':get_temp} ]

    fc = Furnace_Control(zones)
    
    fc.on(zones[0]['pin'])
    
    time.sleep(2)

    fc.off(zones[0]['pin'])
    
    fc.set_point(zones[0]['name'], 75.0)
    
    fc.start()

    time.sleep(20)
    
    fc.stop()


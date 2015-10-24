import os
import sys
import time
import datetime
import logging
from threading import Lock
from utilities import thread_base
from utilities import config_utils
from utilities import graphite_logging
from utilities.data_logging import value_logger


#
# Example usage:
#
#  t1 = temperature_thread.Temperature_Thread(filename = "main_floor_temps.csv", 
#                                             device_name = ["main_floor_temp"])
#  if t1 != None:
#    t1.start()
#

CONFIG_SEC_NAME = "temperature_thread"

logger = logging.getLogger('allspark.' + CONFIG_SEC_NAME)

class Temperature_Thread(thread_base.AS_Thread):
    def __init__(self, object_group, config):
        thread_base.AS_Thread.__init__(self, CONFIG_SEC_NAME)
        
        self.og = object_group
        
        self.mutex = Lock()
        
        self.current_temps = {}
        
        if not config_utils.check_config_section( config, CONFIG_SEC_NAME ):
            return

        self.data_directory = config_utils.get_config_param( config, CONFIG_SEC_NAME, "data_directory")
        if self.data_directory == None:
            return

        self.device_names = self.og.spark.getDeviceNames(postfix="_floor_temp")
        
        for device in self.device_names:
            self.current_temps[device] = None
        self.current_average_temperature = 0.0

        # Create the data directory if it does not exist
        if not os.path.exists(self.data_directory):
            os.makedirs(self.data_directory)
        
        
        self.data_logger = value_logger.Value_Logger(self.data_directory, "temperatures", self.device_names)
        
        self._initialized = True
        
        
    
    @staticmethod
    def get_template_config(config):
        config.add_section(CONFIG_SEC_NAME)
        config.set(CONFIG_SEC_NAME,"data_directory", "data")
        config.set(CONFIG_SEC_NAME,"temp_data_dir", "%(data_directory)s/temperature_data")
        config.set(CONFIG_SEC_NAME, "data_file", "%(temp_data_dir)s/today.csv")
    
    def getDeviceNames(self):
        if not self._initialized:
            logger.warning( "Warning: getDeviceNames called before _initialized" )
            return []
        
        return self.device_names
    
    def getPrettyDeviceNames(self):
        if not self._initialized:
            logger.warning( "Warning: getPrettyDeviceNames called before _initialized" )
            return []
        
        return self.og.spark.getPrettyDeviceNames(postfix="_floor_temp")
    
    
    def private_run(self):
        logger.info( "Thread executing" )
    
        temps = []
        x = 0.0
        count = 0
        for device in self.device_names:
          
            device_temp = self.og.spark.getVariable(device, "temperature")
          
            try:
                x = x + float(device_temp)
                self.current_temps[device] = float(device_temp)
                count = count + 1
                graphite_logging.send_data(logger.name+"."+device, self.current_temps[device])
                
            except (KeyboardInterrupt, SystemExit):
                raise
            
            except:
                logger.error( "Error getting temperature ("+device+") setting to null" )
                device_temp = "null"
                self.current_temps[device] = None
                
            finally:
                temps.append( device_temp )
      
        if count > 0:
            self.current_average_temperature = x / count
        
        # Store the data
        self.data_logger.add_data( temps )
        
        for _ in range(120):
            if self._running:
                time.sleep(1)
  
    def get_average_temp(self):
        return self.current_average_temperature
    
    def get_current_device_temp(self, device):
        if device in self.current_temps:
            if None == self.current_temps[device]:
                return -1000.0
            else:
                return self.current_temps[device]
        logger.error( "WARNING:",device,"not found" ) 
        return -1000.0
    
    def get_html(self):
        html = ""
        
        if self.isInitialized():
            html = """
            
            <div id="plot" class="jumbotron">
                <h2>Plot</h2>
                <p class="lead">Current average temperature: %.1f F</p>          <!-- CURR AVERAGE TEMP -->
                <div class="row">
                    <div class="col-md-12">
                        <div id="temp_chart_div" style="height: 500px;"></div>
                    </div>
                </div>
            </div>
    
            """ % self.get_average_temp()
        
        return html
    
    def get_javascript(self):
        jscript = ""
        
        if self.isInitialized():
            jscript = """
              
                function drawTempData(data)
                {
                    %s
                }
                
                function drawTempDataOnReady()
                {
                    $.get("%s", function (data) { drawTempData(data);  })           //   TEMPERATURE DATA FILENAME
                }
                ready_function_array.push( drawTempDataOnReady )
            
            """ % ( self.data_logger.get_google_linechart_javascript("Zone Temperatures", "temp_chart_div"), 
                    self.data_directory + "/today.csv" )
            
        return jscript
    
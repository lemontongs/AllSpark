
import os
import time
import psutil
import logging
from threading import Lock
from utilities import thread_base
from utilities import config_utils
from utilities.data_logging import value_logger

CONFIG_SEC_NAME = "memory_thread"

logger = logging.getLogger('allspark.' + CONFIG_SEC_NAME)

class Memory_Thread(thread_base.AS_Thread):
    def __init__(self, object_group, config):
        thread_base.AS_Thread.__init__(self, CONFIG_SEC_NAME)
        
        self.og = object_group
        
        self.mutex = Lock()
        
        if not config_utils.check_config_section( config, CONFIG_SEC_NAME ):
            return

        self.data_directory = config_utils.get_config_param( config, CONFIG_SEC_NAME, "data_directory")
        if self.data_directory == None:
            return

        if "collect_period" not in config.options( CONFIG_SEC_NAME ):
            self.collect_period = 60
        else:
            self.collect_period = float(config.get( CONFIG_SEC_NAME, "collect_period", True ) )
        
        self.data_logger = value_logger.Value_Logger(self.data_directory, "memory", "Percent Used")
        
        self._initialized = True
    
    @staticmethod
    def get_template_config(config):
        config.add_section(CONFIG_SEC_NAME)
        config.set(CONFIG_SEC_NAME, "temp_data_dir", "data")
        config.set(CONFIG_SEC_NAME, "data_directory", "%(temp_data_dir)s/memory_data")
        
    def private_run(self):
        
        percent_used = psutil.phymem_usage().percent
        
        self.data_logger.add_data( [ str(percent_used) ] )
        logger.debug("Got:" + str(percent_used) )
        
        for _ in range(self.collect_period):
            if self._running:
                time.sleep(1)
  
    def get_html(self):
        html = ""
        
        if self.isInitialized():
            html = """
                <div id="sysinfo" class="jumbotron">
                    <div class="row">
                        <div class="col-md-12">
                            <h2>System Info</h2>
                            <h3>Memory Usage</h3>
                            <div id="mem_chart_div"></div>
                        </div>
                    </div>
                </div>
            """
        
        return html
    
    def get_javascript(self):
        jscript = ""
        
        if self.isInitialized():
            jscript = """
                function drawMemData(data)
                {
                    %s
                }
                
                function drawMemDataOnReady()
                {
                    $.get("%s", function (data) { drawMemData(data);  })
                }
                
                ready_function_array.push( drawMemDataOnReady )
                
                """ % ( self.data_logger.get_google_linechart_javascript("Memory Usage", "mem_chart_div"), 
                        self.data_directory+"/today.csv" )
            
        return jscript
    
            
if __name__ == "__main__":
    
    mem = Memory_Thread(filename = "mem_usage.csv", collect_period = 2)
    
    if not mem.isInitialized():
        print "ERROR: initialization failed"
        os._exit(0)
    
    mem.start()
    
    print "Collecting data (1 minute)..."
    time.sleep(60)
    
    mem.stop()

            
            
            
            
            
            
            
            
            
            
            
            

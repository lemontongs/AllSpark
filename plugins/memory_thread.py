
import time
import psutil
from threading import Lock
from utilities.thread_base import ThreadedPlugin
from utilities import config_utils
from utilities.data_logging import value_logger

PLUGIN_NAME = "memory_thread"


class MemoryMonitorPlugin(ThreadedPlugin):

    @staticmethod
    def get_dependencies():
        return []

    def __init__(self, object_group, config):
        ThreadedPlugin.__init__(self, config=config, object_group=object_group, plugin_name=PLUGIN_NAME)

        self.mutex = Lock()
        
        if not self.enabled:
            return

        self.data_directory = config_utils.get_config_param(config, PLUGIN_NAME, "data_directory", self.logger)
        if self.data_directory is None:
            return

        if "collect_period" not in config.options(PLUGIN_NAME):
            self.collect_period = 60
        else:
            self.collect_period = float(config.get(PLUGIN_NAME, "collect_period", True))
        
        self.data_logger = value_logger.ValueLogger(self.data_directory, "memory", "Percent Used")
        
        self._initialized = True
    
    @staticmethod
    def get_template_config(config):
        config.add_section(PLUGIN_NAME)
        config.set(PLUGIN_NAME, "temp_data_dir", "data")
        config.set(PLUGIN_NAME, "data_directory", "%(temp_data_dir)s/memory_data")
        
    def private_run(self):
        
        percent_used = psutil.phymem_usage().percent
        
        self.data_logger.add_data( [ str(percent_used) ] )
        self.logger.debug("Got:" + str(percent_used) )
        
        for _ in range(self.collect_period):
            if self._running:
                time.sleep(1)
  
    def get_html(self):
        html = ""
        
        if self.is_initialized():
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
        
        if self.is_initialized():
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
                        self.data_directory + "/today.csv" )
            
        return jscript
    
            
if __name__ == "__main__":
    import ConfigParser

    conf = ConfigParser.ConfigParser()

    MemoryMonitorPlugin.get_template_config(conf)

    mem = MemoryMonitorPlugin(None, conf)
    
    if not mem.is_initialized():
        print "ERROR: initialization failed"

    else:
        mem.start()

        print "Collecting data (1 minute)..."
        time.sleep(60)

        mem.stop()


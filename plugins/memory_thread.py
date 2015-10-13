import csv
import os
import sys
import time
import datetime
import psutil
import logging
from threading import Lock
from utilities import thread_base
from utilities import config_utils

#
# Example usage:
#
#  t1 = temperature_thread.Memory_Thread(filename = "main_floor_temps.csv")
#  if t1.isInitialized():
#    t1.start()
#

CONFIG_SEC_NAME = "memory_thread"

logger = logging.getLogger('allspark.' + CONFIG_SEC_NAME)

class Memory_Thread(thread_base.AS_Thread):
    def __init__(self, object_group, config):
        thread_base.AS_Thread.__init__(self, CONFIG_SEC_NAME)
        
        self.og = object_group
        
        self.mutex = Lock()
        
        if not config_utils.check_config_section( config, CONFIG_SEC_NAME ):
            return

        self.filename = config_utils.get_config_param( config, CONFIG_SEC_NAME, "data_file")
        if self.filename == None:
            return

        if "collect_period" not in config.options( CONFIG_SEC_NAME ):
            self.collect_period = 60
        else:
            self.collect_period = float(config.get( CONFIG_SEC_NAME, "collect_period", True ) )
        
        try:
            self.file_handle = open(self.filename, 'a+')
            self.file_handle.seek(0,2)
        except:
            print "Failed to open", self.filename, ":", sys.exc_info()[1]
            return
        
        self._initialized = True
    
    @staticmethod
    def get_template_config(config):
        config.add_section(CONFIG_SEC_NAME)
        config.set(CONFIG_SEC_NAME, "data_directory", "data")
        config.set(CONFIG_SEC_NAME, "data_file", "%(data_directory)s/mem_usage.csv")
        
    def private_run(self):
        
        self.mutex.acquire()
        try:
            self.file_handle.write(str(time.time()) + "," + str(psutil.phymem_usage().percent) + "\n")
            self.file_handle.flush()
        except:
            self.mutex.release()
            raise
        
        self.mutex.release()
            
        for _ in range(self.collect_period):
            if self._running:
                time.sleep(1)
  
    def private_run_cleanup(self):
        self.file_handle.close()
    
    def get_html(self):
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
        jscript = """
            function drawMemData(data)
            {
                var rows = data.split('\\n');
                
                var result = [['Time','Memory Usage (percent)']];
                
                for ( var i = 0; i < rows.length; i++)
                {
                    var row = rows[i];
                    var items = row.split(",");
                    if (items.length != 2)
                        continue;
                    var time = items[0];
                    var mem_usage = items[1];
                    
                    var d = new Date(0); // The 0 there is the key, which sets the date to the epoch
                    d.setUTCSeconds(parseInt(time));
                    
                    var now = new Date();
                    var days = (now - d)/(1000*60*60*24);
                    if (days > 1.0)
                    {
                        continue;
                    }
                    
                    result.push([d, parseFloat(mem_usage)]);
                }
                
                var data = google.visualization.arrayToDataTable(result);
                var options = { title: 'Memory Usage' };
                var chart = new google.visualization.LineChart(document.getElementById('mem_chart_div'));
                chart.draw(data, options);
            }
            
            function drawMemDataOnReady()
            {
                $.get("%s", function (data) { drawMemData(data);  })
            }
            
            ready_function_array.push( drawMemDataOnReady )
            
            """ % self.filename
        
        return jscript
        
    
    def get_history(self, days=1, seconds=0):
        
        # start_time is "now" minus days and seconds
        # only this much data will be shown
        start_time = datetime.datetime.now() - datetime.timedelta(days,seconds)
        
        # Load the data from the file
        self.mutex.acquire()
        file_handle = open(self.filename, 'r')
        csvreader = csv.reader(file_handle)
        memdata = []
        try:
            for row in csvreader:
                memdata.append(row)
        except csv.Error, e:
            logger.error( 'Memory_Thread: ERROR: file %s, line %d: %s' % (self.filename, csvreader.line_num, e) )
        self.mutex.release()
        
        # Build the return string
        return_string = ""
        for _, row in enumerate(memdata):
            
            # Skip the ones before the start_time
            dt = datetime.datetime.fromtimestamp(float(row[0]))
            if dt < start_time:
                continue
            
            time = dt.strftime('%I:%M:%S %p')
            mem = row[1]
            
            return_string += ("        ['%s',  %s],\n" % (time,mem))
        
        if len(return_string) > 2:
            return_string = return_string[:-2]
        
        return return_string
            
            
if __name__ == "__main__":
    
    mem = Memory_Thread(filename = "mem_usage.csv", collect_period = 2)
    
    if not mem.isInitialized():
        print "ERROR: initialization failed"
        os._exit(0)
    
    mem.start()
    
    print "Collecting data (1 minute)..."
    time.sleep(60)
    
    print mem.get_history()
    
    mem.stop()

            
            
            
            
            
            
            
            
            
            
            
            

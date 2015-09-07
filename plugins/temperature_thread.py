import os
import sys
import time
import datetime
from threading import Thread, Lock


#
# Example usage:
#
#  t1 = temperature_thread.Temperature_Thread(filename = "main_floor_temps.csv", 
#                                             device_name = ["main_floor_temp"])
#  if t1 != None:
#    t1.start()
#

class Temperature_Thread(Thread):
    def __init__(self, object_group, config):
        Thread.__init__(self)
        self.og = object_group
        self.initialized = False
        self.mutex = Lock()
        self.run_lock = Lock()
        self.running = False
        self.current_temps = {}
        config_sec = "temperature_thread"

        if config_sec not in config.sections():
            print config_sec + " section missing from config file"
            return

        if "temp_data_dir" not in config.options(config_sec):
            print "temp_data_dir property missing from " + config_sec + " section"
            return

        if "data_file" not in config.options(config_sec):
            print "data_file property missing from " + config_sec + " section"
            return

        self.filename = config.get(config_sec, "data_file")
        self.device_names = self.og.spark.getDeviceNames(postfix="_floor_temp")
        
        for device in self.device_names:
            self.current_temps[device] = None
        self.current_average_temperature = 0.0

        # Create the data directory if it does not exist
        self.temp_data_directory = config.get(config_sec, "temp_data_dir")
        if not os.path.exists(self.temp_data_directory):
            os.makedirs(self.temp_data_directory)
        
        self.initialized = True
    
    def isInitialized(self):
        return self.initialized
    
    def getDeviceNames(self):
        if not self.initialized:
            print "Warning: getDeviceNames called before initialized"
            return []
        
        return self.device_names
    
    def getPrettyDeviceNames(self):
        if not self.initialized:
            print "Warning: getPrettyDeviceNames called before initialized"
            return []
        
        return self.og.spark.getPrettyDeviceNames(postfix="_floor_temp")
    
    
    def setup_data_file(self):
        
        if not self.initialized:
            print "Warning: Temperature_Thread: setup_data_file called before initialized."
            return
        
        today = datetime.date.today().strftime('temperatures_%Y_%m_%d.csv')
        todays_filename = self.temp_data_directory + "/" + today
        
        # If the file is currently open, close it
        if hasattr(self, 'file_handle') and not self.file_handle.closed:
            self.file_handle.close()
        
        # If the "today" link exists, delete it
        if os.path.islink(self.filename):
            os.unlink(self.filename)
        
        # Touch todays data file (does nothing if it already exists)
        open(todays_filename, 'a').close()
        
        # Create the "today" link to todays data file
        os.symlink(today, self.filename)
        
        # Open the link as a data file
        try:
            self.file_handle = open(self.filename, 'a+')
            self.file_handle.seek(0,2)
        except:
            print "Temperature_Thread: Failed to open", self.filename, ":", sys.exc_info()[1]
            return
        
    
    def run(self):
        
        if not self.initialized:
            print "Warning: Temperature_Thread started before initialized, not running."
            return
        
        self.setup_data_file()
        
        last_day = time.localtime().tm_mday
        
        self.running = self.run_lock.acquire()
        while self.running:
          
            t = {}
            x = 0.0
            count = 0
            for device in self.device_names:
              
                t[device] = self.og.spark.getVariable(device, "temperature")
              
                try:
                    x = x + float(t[device])
                    self.current_temps[device] = float(t[device])
                    count = count + 1
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    print "Error getting temperature ("+device+") setting to null"
                    t[device] = "null"
                    self.current_temps[device] = None
          
            if count > 0:
                self.current_average_temperature = x / count
            
            # Check if file needs to be changed
            self.mutex.acquire()
            now = time.time()
            if time.localtime(now).tm_mday != last_day:
                last_day = time.localtime(now).tm_mday
                self.setup_data_file()
            
            # Write to the file
            self.file_handle.write(str(now))
            for device in self.device_names:
                self.file_handle.write("," + t[device])
            self.file_handle.write("\n")
            self.file_handle.flush()
            self.mutex.release()
            
            for _ in range(120):
                if self.running:
                    time.sleep(1)
        
        self.run_lock.release()
  
    def stop(self):
        self.running = False
        self.run_lock.acquire() # Wait for the thread to stop
        self.file_handle.close()
    
    def get_average_temp(self):
        return self.current_average_temperature
    
    def get_current_device_temp(self, device):
        if device in self.current_temps:
            if None == self.current_temps[device]:
                return -1000.0
            else:
                return self.current_temps[device]
        print "WARNING:",device,"not found" 
        return -1000.0
    
    def get_html(self):
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
        jscript = """
        """
        
        return jscript
    
#    def get_history(self, days=1, seconds=0):
#        
#        # start_time is "now" minus days and seconds
#        # only this much data will be shown
#        start_time = datetime.datetime.now() - datetime.timedelta(days,seconds)
#        
#        # Load the data from the file
#        self.mutex.acquire()
#        file_handle = open(self.filename, 'r')
#        csvreader = csv.reader(file_handle)
#        tempdata = []
#        try:
#            for row in csvreader:
#                tempdata.append(row)
#        except csv.Error, e:
#            print 'ERROR: file %s, line %d: %s' % (self.filename, csvreader.line_num, e)
#        self.mutex.release()
#        
#        # Build the return string
#        return_string = ""
#        for i, row in enumerate(tempdata):
#            
#            # Skip the ones before the start_time
#            dt = datetime.datetime.fromtimestamp(float(row[0]))
#            if dt < start_time:
#                continue
#            
#            time = dt.strftime('%I:%M:%S %p')
#            temp1 = row[1]
#            temp2 = row[2]
#            temp3 = row[3]
#            
#            return_string += ("        ['%s',  %s, %s, %s],\n" % (time,temp1,temp2,temp3))
#        
#        if len(return_string) > 2:
#            return_string = return_string[:-2]
#        
#        return return_string
            
            
            
            
            
            
            
            
            
            
            
            
            
            

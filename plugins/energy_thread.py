import copy
import os
import time
import logging
import subprocess
import Queue
import json
import signal
import sys
import shlex
from datetime import datetime
from threading import Lock, Thread
from utilities import config_utils
from utilities import thread_base
from utilities.data_logging import value_logger

ON_POSIX = 'posix' in sys.builtin_module_names
AMR_ARGS = " -msgtype=idm -format=json -decimation=8 "

CONFIG_SEC_NAME = "energy_thread"

logger = logging.getLogger('allspark.' + CONFIG_SEC_NAME)


class Energy_Thread(thread_base.AS_Thread):
    def __init__(self, object_group, config):
        thread_base.AS_Thread.__init__(self, CONFIG_SEC_NAME)
        
        self.og = object_group
        self.mutex = Lock()
        
        if not config_utils.check_config_section( config, CONFIG_SEC_NAME ):
            return

        self.data_directory = config_utils.get_config_param( config, CONFIG_SEC_NAME, "data_directory")
        if self.data_directory == None:
            return

        rtl_exe = config_utils.get_config_param( config, CONFIG_SEC_NAME, "rtl_tcp_exe")
        if rtl_exe == None or not os.path.isfile(rtl_exe):
            return

        rtl_ppm = config_utils.get_config_param( config, CONFIG_SEC_NAME, "rtl_ppm")
        rtl_ppm_args = ""
        if rtl_ppm:
            rtl_ppm_args = " -freqcorrection="+rtl_ppm
        
        amr_exe = config_utils.get_config_param( config, CONFIG_SEC_NAME, "rtl_amr_exe")
        if amr_exe == None or not os.path.isfile(amr_exe):
            return

        self.meter_serial_number = config_utils.get_config_param( config, CONFIG_SEC_NAME, "meter_serial_number")
        if self.meter_serial_number == None:
            return
        self.meter_serial_number = int( self.meter_serial_number )
        filter_args = " -filterid="+str( self.meter_serial_number )
        
        #
        # start rtl_tcp
        #
        logger.debug( "RTL_TCP commmand: " + rtl_exe )
        self.rtl_handle = subprocess.Popen(shlex.split(rtl_exe), 
                                           stdout=subprocess.PIPE, 
                                           stderr=subprocess.STDOUT, 
                                           bufsize=1, 
                                           close_fds=ON_POSIX)
        
        time.sleep(5)
        
        # start rtlamr with a thread that fills the queue with each line of output
        logger.debug( "RTL_AMR commmand: " + amr_exe + AMR_ARGS + rtl_ppm_args + filter_args )
        self.amr_handle = subprocess.Popen(shlex.split(amr_exe + AMR_ARGS + rtl_ppm_args + filter_args), 
                                           stdout=subprocess.PIPE, 
                                           stderr=subprocess.STDOUT, 
                                           bufsize=1, 
                                           close_fds=ON_POSIX)
        
        self.todays_starting_consumption = None
        self.total_consumption = 0.0
        self.todays_consumption = 0.0
        self.yesterdays_consumption = 0.0
        self.packets = Queue.Queue()
        self.last_day = time.localtime().tm_mday
        
        self.data_logger = value_logger.Value_Logger(self.data_directory, "energy", "Electricity Used")
        
        # Setup the initial values from the previously logged data
        today_data = self.data_logger.get_data_set()
        if today_data and len(today_data) > 0:
            
            self.total_consumption           = float( today_data[-1]['data'][0] )
            self.todays_starting_consumption = float( today_data[0]['data'][0] )
            self.todays_consumption          = self.total_consumption - self.todays_starting_consumption
            
            logger.info( "Initial data: total:           %.2f" % self.total_consumption )
            logger.info( "Initial data: todays_starting: %.2f" % self.todays_starting_consumption )
            logger.info( "Initial data: todays:          %.2f" % self.todays_consumption )
        
        yesterday_data = self.data_logger.get_data_set(-2)
        if yesterday_data and len(yesterday_data) > 0:
            self.yesterdays_consumption = float( yesterday_data[-1]['data'][0] ) - float( yesterday_data[0]['data'][0] )
            logger.info( "Initial data: yesterday:       %.2f" % self.yesterdays_consumption )
            
            
        def enqueue_output(out, queue):
            f = open("logs/rtlamr.log",'w')
            for line in iter(out.readline, b''):
                queue.put(line.rstrip())
                f.write(line)
            f.close()
        
        self.output_thread = Thread( target = enqueue_output, args = (self.amr_handle.stdout, self.packets) )
        self.output_thread.daemon = True # thread dies with the program
        self.output_thread.start()
        
        time.sleep(5)

        if self.rtl_handle.returncode != None:
            logger.warning( "RTL_TCP exited with code:", str(self.rtl_handle.returncode) ) 
            return
            
        if self.amr_handle.returncode != None:
            logger.warning( "RTL_AMR exited with code:", str(self.amr_handle.returncode) ) 
            return
        
        self._initialized = True
    
    
    def private_run(self):
        if self.isInitialized():
            if self.rtl_handle.returncode != None:
                logger.warning( "RTL_TCP exited with code: " + str(self.rtl_handle.returncode) )
                self._running = False
                return
                
            if self.amr_handle.returncode != None:
                logger.warning( "RTL_AMR exited with code: " + str(self.amr_handle.returncode) )
                self._running = False
                return
            
            # read line with timeout
            try: 
                line = self.packets.get(timeout=1)
            except Queue.Empty:
                pass
            else: # got line
                try:
                    logger.debug( "Got line: " + line )
                    
                    packet = json.loads(line)
                    
                    if 'Message'              in packet            and \
                       'ERTSerialNumber'      in packet['Message'] and \
                       'LastConsumptionCount' in packet['Message']:
                         
                        serial = packet['Message']['ERTSerialNumber']
                        consumption = copy.deepcopy( float( int( packet['Message']['LastConsumptionCount'] ) / 100.0 ) ) # Convert to kWh
                        
                        # Check for a match
                        if serial == self.meter_serial_number:
                            
                            if self.todays_starting_consumption == None:
                                self.todays_starting_consumption = consumption
                            
                            # Save the data
                            self.data_logger.add_data([str(consumption)])
                            
                            self.total_consumption = consumption
                            self.todays_consumption = consumption - self.todays_starting_consumption
                            
                            # New day transition
                            now = time.time()
                            if time.localtime(now).tm_mday != self.last_day:
                                self.last_day = time.localtime(now).tm_yday
                                self.yesterdays_consumption = self.todays_consumption
                                self.todays_consumption = 0
                                self.todays_starting_consumption = consumption
                                
                            logger.info( "Total: %.2f  Today: %.2f Yesterday: %.2f" % ( self.total_consumption,
                                                                                        self.todays_consumption,
                                                                                        self.yesterdays_consumption ) )
                        else:
                            logger.debug( "NO MATCH" )
                        
                except ValueError:
                    logger.debug( "Error parsing json" )
                            
                for _ in range(1):
                    if self._running:
                        time.sleep(1)

    def get_total_consumption(self):
        return self.total_consumption
    
    def get_todays_consumption(self):
        return self.todays_consumption
    
    def get_yesterdays_consumption(self):
        return self.yesterdays_consumption

    def private_run_cleanup(self):  
        if self.isInitialized():      
            
            if self.rtl_handle.returncode == None:
                logger.info( "killing: " + str(self.amr_handle.pid) )
                os.kill(self.amr_handle.pid, signal.SIGKILL)
                
            if self.amr_handle.returncode == None:
                logger.info( "killing: " + str(self.rtl_handle.pid) )
                os.kill(self.rtl_handle.pid, signal.SIGKILL)
    
        
    @staticmethod
    def get_template_config(config):
        config.add_section(CONFIG_SEC_NAME)
        config.set(CONFIG_SEC_NAME,"rtl_tcp_exe", "/<path>/<to>/rtl_tcp")
        config.set(CONFIG_SEC_NAME,"rtl_ppm", "0")
        config.set(CONFIG_SEC_NAME,"rtl_amr_exe", "/<path>/<to>/rtlamr")
        config.set(CONFIG_SEC_NAME,"meter_serial_number", "5555555555")
        
    def get_html(self):
        if self.isInitialized():
            html = """
                <div id="energy" class="jumbotron">
                    <div class="row">
                        <div class="col-md-12">
                            <h2>Energy:</h2>
                            <p>Yesterday: %.2f kWh</p>
                            <p>Today: %.2f kWh</p>
                            <p>Total: %.2f kWh</p>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-12">
                            <div id="today_energy_chart_div"></div>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-12">
                            <div id="history_energy_chart_div"></div>
                        </div>
                    </div>
                </div>
            """ % ( self.get_yesterdays_consumption(), 
                    self.get_todays_consumption(), 
                    self.get_total_consumption() )
        
            return html
        return ""
    
    def get_javascript(self):
        if self.isInitialized():
            jscript = """
            function drawEnergyData(data)
            {
                %s
            }
            
            function drawEnergyDataOnReady()
            {
                $.get("%s", function (data) { drawEnergyData(data);  })
            }
            
            ready_function_array.push( drawEnergyDataOnReady )
            
            """ % ( self.data_logger.get_google_linechart_javascript("Energy Usage", "today_energy_chart_div"),
                    self.data_directory + "/today.csv" )
            
            #
            # Now generate a bar chart of the past days, only if data for past days exists
            #
            num_data_sets = self.data_logger.num_data_sets()
            if num_data_sets > 1:
                
                array_string = ""
                
                for set_index in range(-num_data_sets,0):
                    first = self.data_logger.get_data_item(dataset=set_index, index=0)
                    last  = self.data_logger.get_data_item(dataset=set_index, index=-1)
                    
                    if first == None or last == None:
                        continue
                    
                    dt = datetime.fromtimestamp(first['time'])
                    year   = dt.strftime('%Y')
                    month  = str(int(dt.strftime('%m')) - 1) # javascript expects month in 0-11, strftime gives 1-12 
                    day    = dt.strftime('%d')
                    date_str = 'new Date(%s,%s,%s)' % (year,month,day)
                    
                    usage = float( last['data'][0] ) - float( first['data'][0] )
                    
                    array_string += "[ %s, %.2f ],\n" % ( date_str, usage )
                    
                # Remove the trailing comma and return line    
                if len(array_string) > 2:
                    array_string = array_string[:-2]
        
                    
                
                jscript += """
                
                function drawEnergyHistoryData(data)
                {
                    var dataTable = new google.visualization.DataTable();
                    
                    dataTable.addColumn({ type: 'date',   id: 'Time of Day' });
                    dataTable.addColumn({ type: 'number', id: 'Energy Used' });
                    
                    dataTable.addRows([
                    
                    %s             //   ENERGY DATA
            
                    ]);
            
                    chart = new google.visualization.ColumnChart(document.getElementById('history_energy_chart_div'));
                    chart.draw(dataTable);
                }
                
                ready_function_array.push( drawEnergyHistoryData )
                
                """ % array_string
                
            return jscript
        return ""
        
        
        
        
        
        
if __name__ == "__main__":
    from ConfigParser import ConfigParser
    
    logging.getLogger('').handlers = []
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    format_str = '%(asctime)s %(name)-30s %(levelname)-8s %(message)s'
    console.setFormatter(logging.Formatter(format_str))
    logger.addHandler(console)
    
    config = ConfigParser()
    config.add_section(CONFIG_SEC_NAME)
    config.set(CONFIG_SEC_NAME,"rtl_tcp_exe", "/usr/local/bin/rtl_tcp")
    config.set(CONFIG_SEC_NAME,"rtl_ppm", "51")
    config.set(CONFIG_SEC_NAME,"rtl_amr_exe", "/home/mlamonta/git/rtlamr/bin/rtlamr")
    config.set(CONFIG_SEC_NAME,"meter_serial_number", "69148036")
    
    eng = Energy_Thread( 1, config )
    
    if not eng.isInitialized():
        print "ERROR: initialization failed"
        os._exit(0)
    
    print "Collecting data..."
    
    eng.start()
    
    try:
        while eng.get_total_consumption() == 0:
            time.sleep(5)
        
        print "Total: %f  Today: %f Yesterday: %f" % ( eng.get_total_consumption(),
                                                       eng.get_todays_consumption(),
                                                       eng.get_yesterdays_consumption() )
    finally:
        eng.stop()

            
            
            
            
            
            
            
            
            
            
            
            

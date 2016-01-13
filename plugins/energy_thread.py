
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
from utilities.thread_base import ThreadedPlugin
from utilities.data_logging import value_logger

ON_POSIX = 'posix' in sys.builtin_module_names
AMR_ARGS = " -msgtype=idm -format=json -decimation=8 "

PLUGIN_NAME = "energy_thread"


class EnergyMonitorPlugin(ThreadedPlugin):

    @staticmethod
    def get_dependencies():
        return []

    def __init__(self, object_group, config):
        ThreadedPlugin.__init__(self, config=config, object_group=object_group, plugin_name=PLUGIN_NAME)

        self.mutex = Lock()

        if not self.is_enabled():
            return

        self.data_directory = config_utils.get_config_param(config, PLUGIN_NAME, "data_directory", self.logger)
        if self.data_directory is None:
            return

        rtl_exe = config_utils.get_config_param(config, PLUGIN_NAME, "rtl_tcp_exe", self.logger)
        if rtl_exe is None:
            return

        if not os.path.isfile(rtl_exe):
            self.logger.warning("Could not access: " + rtl_exe)
            return

        rtl_ppm = config_utils.get_config_param(config, PLUGIN_NAME, "rtl_ppm", self.logger)
        rtl_ppm_args = ""
        if rtl_ppm:
            rtl_ppm_args = " -freqcorrection=" + rtl_ppm
        
        amr_exe = config_utils.get_config_param(config, PLUGIN_NAME, "rtl_amr_exe", self.logger)
        if amr_exe is None:
            return

        if not os.path.isfile(amr_exe):
            self.logger.warning("Could not access: " + rtl_exe)
            return

        self.meter_serial_number = \
            config_utils.get_config_param(config, PLUGIN_NAME, "meter_serial_number", self.logger)
        if self.meter_serial_number is None:
            return
        self.meter_serial_number = int( self.meter_serial_number )
        filter_args = " -filterid=" + str( self.meter_serial_number )
        
        #
        # start rtl_tcp
        #
        self.logger.debug( "RTL_TCP commmand: " + rtl_exe )
        self.rtl_handle = subprocess.Popen(shlex.split(rtl_exe), 
                                           stdout=subprocess.PIPE, 
                                           stderr=subprocess.STDOUT, 
                                           bufsize=1, 
                                           close_fds=ON_POSIX)
        
        time.sleep(5)
        
        # start rtlamr with a thread that fills the queue with each line of output
        self.logger.debug( "RTL_AMR commmand: " + amr_exe + AMR_ARGS + rtl_ppm_args + filter_args )
        self.amr_handle = subprocess.Popen(shlex.split(amr_exe + AMR_ARGS + rtl_ppm_args + filter_args), 
                                           stdout=subprocess.PIPE, 
                                           stderr=subprocess.STDOUT, 
                                           bufsize=1, 
                                           close_fds=ON_POSIX)
        
        self.packets = Queue.Queue()
        
        self.data_logger = value_logger.ValueLogger(self.data_directory, "energy", "Electricity Used")

        def enqueue_output(out, queue):
            f = open("logs/rtlamr.log", 'w')
            for line in iter(out.readline, b''):
                queue.put(line.rstrip())
                f.write(line)
            f.close()
        
        self.output_thread = Thread( target = enqueue_output, args = (self.amr_handle.stdout, self.packets) )
        self.output_thread.daemon = True  # thread dies with the program
        self.output_thread.start()
        
        time.sleep(5)

        if self.rtl_handle.returncode is not None:
            self.logger.warning( "RTL_TCP exited with code:", str(self.rtl_handle.returncode) )
            return
            
        if self.amr_handle.returncode is not None:
            self.logger.warning( "RTL_AMR exited with code:", str(self.amr_handle.returncode) )
            return
        
        self._initialized = True

    def private_run(self):
        if self.is_initialized():
            if self.rtl_handle.returncode is not None:
                self.logger.warning( "RTL_TCP exited with code: " + str(self.rtl_handle.returncode) )
                self._running = False
                return
                
            if self.amr_handle.returncode is not None:
                self.logger.warning( "RTL_AMR exited with code: " + str(self.amr_handle.returncode) )
                self._running = False
                return
            
            # read line with timeout
            try: 
                line = self.packets.get(timeout=1)
            except Queue.Empty:
                pass
            else:  # got line
                try:
                    self.logger.debug( "Got line: " + line )
                    
                    packet = json.loads(line)
                    
                    if 'Message'              in packet            and \
                       'ERTSerialNumber'      in packet['Message'] and \
                       'LastConsumptionCount' in packet['Message']:
                         
                        serial = packet['Message']['ERTSerialNumber']
                        # Convert to kWh
                        consumption = copy.deepcopy( float( int( packet['Message']['LastConsumptionCount'] ) / 100.0 ) )
                        
                        # Check for a match
                        if serial == self.meter_serial_number:
                            
                            # Save the data
                            self.data_logger.add_data([str(consumption)])
                            
                        else:
                            self.logger.debug( "NO MATCH" )
                        
                except ValueError:
                    self.logger.debug( "Error parsing json" )
                            
                for _ in range(1):
                    if self._running:
                        time.sleep(1)

    def private_run_cleanup(self):  
        if self.is_initialized():
            
            if self.rtl_handle.returncode is None:
                self.logger.info( "killing: " + str(self.amr_handle.pid) )
                os.kill(self.amr_handle.pid, signal.SIGKILL)
                
            if self.amr_handle.returncode is None:
                self.logger.info( "killing: " + str(self.rtl_handle.pid) )
                os.kill(self.rtl_handle.pid, signal.SIGKILL)

    @staticmethod
    def get_template_config(config):
        config.add_section(PLUGIN_NAME)
        config.set(PLUGIN_NAME, "rtl_tcp_exe", "/<path>/<to>/rtl_tcp")
        config.set(PLUGIN_NAME, "rtl_ppm", "0")
        config.set(PLUGIN_NAME, "rtl_amr_exe", "/<path>/<to>/rtlamr")
        config.set(PLUGIN_NAME, "meter_serial_number", "5555555555")
        
    def get_html(self):
        if self.is_initialized():
            html = """
                <div id="energy" class="jumbotron">
                    <div class="row">
                        <div class="col-md-12">
                            <h2>Energy:</h2>
                            <div id="today_energy_chart_div"></div>
                            <div id="history_energy_chart_div"></div>
                        </div>
                    </div>
                </div>
            """
        
            return html
        return ""
    
    def get_javascript(self):
        if self.is_initialized():
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
                
                for set_index in range(-num_data_sets, 0):
                    first = self.data_logger.get_data_item(dataset=set_index, index=0)
                    last  = self.data_logger.get_data_item(dataset=set_index, index=-1)
                    
                    if first is None or last is None:
                        continue
                    
                    dt = datetime.fromtimestamp(first['time'])
                    year   = dt.strftime('%Y')
                    month  = str(int(dt.strftime('%m')) - 1)  # javascript expects month in 0-11, strftime gives 1-12
                    day    = dt.strftime('%d')
                    date_str = 'new Date(%s,%s,%s)' % (year, month, day)
                    
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
    logging.getLogger("AllSPark." + PLUGIN_NAME).addHandler(console)
    
    conf = ConfigParser()
    conf.add_section(PLUGIN_NAME)
    conf.set(PLUGIN_NAME, "rtl_tcp_exe", "/usr/local/bin/rtl_tcp")
    conf.set(PLUGIN_NAME, "rtl_ppm", "51")
    conf.set(PLUGIN_NAME, "rtl_amr_exe", "/home/mlamonta/git/rtlamr/bin/rtlamr")
    conf.set(PLUGIN_NAME, "meter_serial_number", "69148036")
    
    eng = EnergyMonitorPlugin(1, conf)
    
    if not eng.is_initialized():
        print "ERROR: initialization failed"

    else:
        print "Collecting data..."

        eng.start()
        time.sleep(50)
        eng.stop()

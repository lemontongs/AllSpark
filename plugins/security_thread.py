
import os
import time
from threading import Thread, Lock
from utilities import udp_interface
from utilities import logger

OPEN   = '0'
CLOSED = '1'

CONFIG_SEC_NAME = "security_thread"

class Security_Thread(Thread):
    def __init__(self, object_group, config):
        Thread.__init__(self)
        self.og = object_group
        self.initialized = False
        self.mutex = Lock()
        self.running = False
        config_sec = CONFIG_SEC_NAME

        if config_sec not in config.sections():
            print config_sec + " section missing from config file"
            return

        if "monitor_device_name" not in config.options(config_sec):
            print "monitor_device_name property missing from " + config_sec + " section"
            return
        self.monitor_device_name = config.get(config_sec, "monitor_device_name")

        if "breach_number" not in config.options(config_sec):
            print "breach_number property missing from " + config_sec + " section"
            return
        self.breach_number = int(config.get(config_sec, "breach_number"))
        
        if "num_zones" not in config.options(config_sec):
            print "num_zones property missing from " + config_sec + " section"
            return
        self.num_zones = int(config.get(config_sec, "num_zones"))
        
        if "data_directory" not in config.options(config_sec):
            print "data_directory property missing from " + config_sec + " section"
            return
        data_directory = config.get(config_sec, "data_directory")
        
        if "data_file" not in config.options(config_sec):
            print "data_file property missing from " + config_sec + " section"
            return
        data_file = config.get(config_sec, "data_file")
        
        self.zones = []
        zone_names = []
        
        for zone in range(self.num_zones):
            zone_index = "zone_"+str(zone)
            
            if zone_index not in config.options(config_sec):
                print zone_index+" property missing from " + config_sec + " section"
                return
                
            self.zones.append( {'last':time.localtime(), 'state':CLOSED, 'name':config.get(config_sec, zone_index)} )
            zone_names.append( config.get(config_sec, zone_index) )

        #print self.zones

        if "collect_period" not in config.options(config_sec):
            self.collect_period = 5
        else:
            self.collect_period = float(config.get(config_sec, "collect_period", True))
        
        # Setup data logger
        self.data_logger = logger.Logger( data_directory, data_file, "security", zone_names ) 
        
        # Setup UDP interface
        self.udp = udp_interface.UDP_Interface( config )
        
        if not self.udp.isInitialized():
            return
        
        self.sensor_states = ""
        self.initialized = True
    
    @staticmethod
    def get_template_config(config):
        config.add_section(CONFIG_SEC_NAME)
        config.set(CONFIG_SEC_NAME,"temp_data_dir", "data")
        config.set(CONFIG_SEC_NAME,"data_directory", "%(temp_data_dir)s/security_data")
        config.set(CONFIG_SEC_NAME,"data_file", "%(data_directory)s/today.csv")
        config.set(CONFIG_SEC_NAME,"breach_number", "+15551231234")
        config.set(CONFIG_SEC_NAME,"monitor_device_name", "<particle security device name>")
        config.set(CONFIG_SEC_NAME,"num_zones", "5")
        config.set(CONFIG_SEC_NAME,"zone_0", "<zone 0 name>")
        config.set(CONFIG_SEC_NAME,"zone_1", "<zone 1 name>")
        config.set(CONFIG_SEC_NAME,"zone_2", "<zone 2 name>")
        config.set(CONFIG_SEC_NAME,"zone_3", "<zone 3 name>")
        config.set(CONFIG_SEC_NAME,"zone_4", "<zone 4 name>")
        
        
    def isInitialized(self):
        return self.initialized
    
    def getSensorStates(self):
        self.mutex.acquire()
        ss = self.sensor_states
        self.mutex.release()
        return ss
    
    def stop(self):
        self.running = False
        self.udp.stop()
    
    def get_html(self):
        html = """
            <div id="security" class="jumbotron">
                <div class="row">
                    <div class="col-md-12">
                        <h2>Security:</h2>
                        <table class="table table-condensed">
                            <thead>
                                <tr>
                                    <th>Zone</th>
                                    <th>State</th>
                                    <th>Last Change</th>
                                </tr>
                            </thead>
                            <tbody>
                                %s               <!-- SECURITY STATE -->
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-12">
                        <div id="security_chart_div"></div>
                    </div>
                </div>
            </div>
        """ % self.getSensorStates()
        
        return html
    
    def get_javascript(self):
        jscript = """
        
            function drawSecurityData() {
                var dataTable = new google.visualization.DataTable();

                dataTable.addColumn({ type: 'string', id: 'Zone' });
                dataTable.addColumn({ type: 'date', id: 'Start' });
                dataTable.addColumn({ type: 'date', id: 'End' });

                dataTable.addRows([
                  
                %s                             //   SECURITY DATA

                ]);

                chart = new google.visualization.Timeline(document.getElementById('security_chart_div'));
                chart.draw(dataTable, { height: 340 });
            }
            ready_function_array.push( drawSecurityData )
            
        """ % self.data_logger.get_google_chart_string()
        
        return jscript
    
    def run(self):
        
        if not self.initialized:
            print "Warning: Security_Thread started before initialized, not running."
            return
        
        self.udp.start()
        
        self.running = True
        while self.running:
          
            msg = self.udp.get( timeout = self.collect_period )
            
            if msg != None:
                
                # ( ( ip_address, port ), message )
                ( _, state_str ) = msg
                
                if len(state_str) != self.num_zones:
                    print "Invalid message received", msg
                    continue
                
                self.mutex.acquire()
                self.sensor_states = ""
                zones_that_are_open = []
                
                for zone in range(self.num_zones):
                    
                    state = state_str[zone]
                    
                    # Save the closed zones for logging
                    if state == OPEN:
                        zones_that_are_open.append( self.zones[zone]['name'] )
                    
                    # record state changes
                    if state != self.zones[zone]['state']:
                        self.zones[zone]['state'] = state
                        self.zones[zone]['last']  = time.localtime()
                        
                        # If nobody is home and something has changed, trigger a warning
                        if not self.og.user_thread.someone_is_present():
                            print "SECURITY BREACH!"
                            self.og.twilio.sendSMS("SECURITY BREACH! "+self.zones[zone]['name'], self.breach_number)
        
                    # <tr class="success">
                    #     <td>Zone 1</td>
                    #     <td>Open</td>
                    #     <td>Yesterday</td>
                    # </tr>
                    entry = '\n<tr class="'
                    if state == CLOSED:
                        entry += 'success">\n'
                    else:
                        entry += 'danger">\n'
                    
                    entry += '    <td>'+self.zones[zone]['name']+'</td>\n'
                    
                    if state == CLOSED:
                        entry += "    <td>closed</td>\n"
                    else:
                        entry += "    <td>open</td>\n"
                    
                    entry += '    <td>'+ time.strftime('%b %d %I:%M%p', self.zones[zone]['last']) +'</td>\n'
                    entry += '</tr>\n'
                    
                    self.sensor_states += entry
                
                self.data_logger.add_data( zones_that_are_open )
                
                self.mutex.release()        
        
        
if __name__ == "__main__":
    
    sec = Security_Thread()
    
    if not sec.isInitialized():
        print "ERROR: initialization failed"
        os._exit(0)
    
    sec.start()
    
    print "Collecting data (1 minute)..."
    time.sleep(60)
    
    #print sec.get_history()
    
    sec.stop()

            
            
            
            
            
            
            
            
            
            
            
            

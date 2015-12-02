
import os
import time
import logging
from threading import Lock
from utilities import udp_interface
from utilities.data_logging import presence_logger
from utilities import config_utils
from utilities import thread_base

OPEN   = '0'
CLOSED = '1'

CONFIG_SEC_NAME = "security_thread"

logger = logging.getLogger('allspark.' + CONFIG_SEC_NAME)

class Security_State():
    
    _NORMAL = 1
    _TRIGGERED = 2
    _state = _NORMAL
    _trigger_time = time.time()
    triggered_zones = []
    
    def __init__(self, delay = 30): # number of seconds to wait before alarming
        self.delay = delay
    
    def clear(self):
        logger.debug("security_state.clear")
        self._state = self._NORMAL
        
    def trigger(self, zone):
        logger.debug("security_state.trigger (zone = %s)" % zone )
        if self._state == self._NORMAL:
            self._state = self._TRIGGERED
            self._trigger_time = time.time()
        
        if self._state == self._TRIGGERED:
            if zone not in self.triggered_zones:
                self.triggered_zones.append(zone)
        
    def should_alarm(self):
        if self._state == self._TRIGGERED:
            if time.time() - self._trigger_time > self.delay:
                logger.debug("security_state.alarm")
                return True
        
        return False



class Security_Thread(thread_base.AS_Thread):
    def __init__(self, object_group, config):
        thread_base.AS_Thread.__init__(self, CONFIG_SEC_NAME)
        
        self.og = object_group
        self.mutex = Lock()
        
        if not config_utils.check_config_section( config, CONFIG_SEC_NAME ):
            return

        self.monitor_device_name = config_utils.get_config_param( config, CONFIG_SEC_NAME, "monitor_device_name")
        if self.monitor_device_name == None:
            return

        self.breach_number = config_utils.get_config_param( config, CONFIG_SEC_NAME, "breach_number")
        if self.breach_number == None:
            return

        self.num_zones = config_utils.get_config_param( config, CONFIG_SEC_NAME, "num_zones")
        if self.num_zones == None:
            return
        self.num_zones = int( self.num_zones )

        data_directory = config_utils.get_config_param( config, CONFIG_SEC_NAME, "data_directory")
        if data_directory == None:
            return

        address = config_utils.get_config_param( config, CONFIG_SEC_NAME, "address")
        if address == None:
            return

        port = config_utils.get_config_param( config, CONFIG_SEC_NAME, "port")
        if port == None:
            return
        
        self.zones = []
        zone_names = []
        
        for zone in range(self.num_zones):
            zone_index = "zone_"+str(zone)
            
            if zone_index not in config.options(CONFIG_SEC_NAME):
                print zone_index+" property missing from " + CONFIG_SEC_NAME + " section"
                return
                
            self.zones.append( { 'last':time.localtime(), \
                                 'state':CLOSED, \
                                 'name':config.get(CONFIG_SEC_NAME, zone_index)} )
            
            zone_names.append( config.get(CONFIG_SEC_NAME, zone_index) )

        #print self.zones

        if "collect_period" not in config.options(CONFIG_SEC_NAME):
            self.collect_period = 10
        else:
            self.collect_period = float(config.get(CONFIG_SEC_NAME, "collect_period", True))
        
        # Setup data data_logger
        self.data_logger = presence_logger.Presence_Logger( data_directory, "security", zone_names ) 
        
        # Setup UDP interface
        self.udp = udp_interface.UDP_Socket( address, port, port, CONFIG_SEC_NAME+"_inf" )
        if not self.udp.isInitialized():
            return
        self.udp.start()
        
        self.security_state = Security_State()
        
        self.sensor_states = ""
        self._initialized = True
    
    @staticmethod
    def get_template_config(config):
        config.add_section(CONFIG_SEC_NAME)
        config.set(CONFIG_SEC_NAME,"temp_data_dir", "data")
        config.set(CONFIG_SEC_NAME,"data_directory", "%(temp_data_dir)s/security_data")
        config.set(CONFIG_SEC_NAME,"breach_number", "+15551231234")
        config.set(CONFIG_SEC_NAME,"monitor_device_name", "<particle security device name>")
        config.set(CONFIG_SEC_NAME,"num_zones", "5")
        config.set(CONFIG_SEC_NAME,"zone_0", "<zone 0 name>")
        config.set(CONFIG_SEC_NAME,"zone_1", "<zone 1 name>")
        config.set(CONFIG_SEC_NAME,"zone_2", "<zone 2 name>")
        config.set(CONFIG_SEC_NAME,"zone_3", "<zone 3 name>")
        config.set(CONFIG_SEC_NAME,"zone_4", "<zone 4 name>")
        
    def getSensorStates(self):
        self.mutex.acquire()
        ss = self.sensor_states
        self.mutex.release()
        return ss
    
    def get_html(self):
        html = ""
        
        if self.isInitialized():
            
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
        jscript = ""
        
        if self.isInitialized():
            jscript = """
                function drawSecurityData()
                {
                    %s
                }
                ready_function_array.push( drawSecurityData )
                
            """ % self.data_logger.get_google_timeline_javascript("Security State", "Zone","security_chart_div", "height: 340")
        
        return jscript
    
    def private_run(self):
        logger.info( "Waiting for message" )
        
        msg = self.udp.get( timeout = self.collect_period )
        
        #
        # Clear the security state
        #
        if self.og.user_thread.someone_is_present():
            self.security_state.clear()
        
        #
        # Check to see if we should sound the alarm!!!
        #
        if self.security_state.should_alarm():
            status = "\nSECURITY BREACH!"
            for zone in self.security_state.triggered_zones:
                status += "\n" + zone
            
            logger.info( status )
            self.og.twilio.sendSMS( status, self.breach_number )
    
        #
        # Process the message
        #
        if msg != None:
            
            # ( ( ip_address, port ), message )
            ( _, state_str ) = msg
            
            if len(state_str) != self.num_zones:
                logger.warning( "Skipping invalid message!" )
                return
            
            logger.info( "Got message: " + state_str )
            
            self.mutex.acquire()
            try:
                self.sensor_states = ""
                zones_that_are_open = []
                
                for zone in range(self.num_zones):
                    
                    state = state_str[zone]
                    
                    # Save the closed zones for logger
                    if state == OPEN:
                        zones_that_are_open.append( self.zones[zone]['name'] )
                    
                    # record state changes
                    if state != self.zones[zone]['state']:
                        self.zones[zone]['state'] = state
                        self.zones[zone]['last']  = time.localtime()
                        
                        # If nobody is home and something has changed, trigger a warning
                        if not self.og.user_thread.someone_is_present():
                            self.security_state.trigger( self.zones[zone]['name'] )
                        
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
            
            except:
                self.mutex.release()
                raise

            self.mutex.release()

    def private_run_cleanup(self):        
        self.udp.stop()
        
        
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

            
            
            
            
            
            
            
            
            
            
            
            

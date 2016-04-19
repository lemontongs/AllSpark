
import time
from threading import Lock
from utilities import udp_interface
from utilities.data_logging import presence_logger
from utilities import config_utils
from utilities.thread_base import ThreadedPlugin

OPEN   = '0'
CLOSED = '1'

PLUGIN_NAME = "security_thread"


class SecurityState:
    
    _DISARMED = 0
    _ARMED = 1
    _TRIGGERED = 2
    _ALARM = 3

    _string_map = {_DISARMED:  "DISARMED",
                   _ARMED:     "ARMED",
                   _TRIGGERED: "TRIGGERED",
                   _ALARM:     "ALARM"}

    _state = _ARMED
    _trigger_time = time.time()
    triggered_zones = []
    
    def __init__(self, object_group, logger, breach_number, delay = 30):  # number of seconds to wait before alarming
        self.delay = delay
        self.og = object_group
        self.logger = logger
        self.breach_number = breach_number

    def get_state(self):
        return self._state

    def get_state_string(self):
        return self._string_map[self._state]

    def arm_system(self):
        if self._state == self._DISARMED:
            self._state = self._ARMED
            self.logger.info("SYSTEM ARMED")
            self.og.broadcast.send("security:armed")

    def disarm_system(self):
        if self._state != self._DISARMED:
            self._state = self._DISARMED
            self.triggered_zones = []
            self.logger.info("SYSTEM DISARMED")
            self.og.broadcast.send("security:disarmed")

    def clear(self):
        if self._state >= self._TRIGGERED:
            self.logger.debug("security_state.clear")
            self._state = self._ARMED
        
    def trigger(self, zone):
        self.logger.debug( "security_state.trigger (zone = %s)" % zone )
        if self._state == self._ARMED:
            self._state = self._TRIGGERED
            self._trigger_time = time.time()
        
        if self._state >= self._TRIGGERED:
            if zone not in self.triggered_zones:
                self.triggered_zones.append(zone)
        
    def sound_alarm(self):
        # Things that happen only once
        if self._state == self._TRIGGERED:
            if time.time() - self._trigger_time > self.delay:
                self._state = self._ALARM
                self.logger.debug("security_state.alarm")

                status = "\nSECURITY BREACH!"
                for zone in self.triggered_zones:
                    status += "\n" + zone

                self.logger.info(status)
                self.og.twilio.send_sms(status, self.breach_number)
                self.og.broadcast.send("security:" + status)

        # Things that repeat until disarmed
        if self._state == self._ALARM:
            self.og.broadcast.send("security:alarming")


class SecurityPlugin(ThreadedPlugin):

    @staticmethod
    def get_dependencies():
        return ['UserMonitorPlugin']

    def __init__(self, object_group, config):
        ThreadedPlugin.__init__(self, config=config, object_group=object_group, plugin_name=PLUGIN_NAME)

        self.mutex = Lock()
        
        if not self.is_enabled():
            return

        self.monitor_device_name = \
            config_utils.get_config_param(config, PLUGIN_NAME, "monitor_device_name", self.logger)
        if self.monitor_device_name is None:
            return

        self.breach_number = config_utils.get_config_param(config, PLUGIN_NAME, "breach_number", self.logger)
        if self.breach_number is None:
            return

        self.num_zones = config_utils.get_config_param(config, PLUGIN_NAME, "num_zones", self.logger)
        if self.num_zones is None:
            return
        self.num_zones = int( self.num_zones )

        data_directory = config_utils.get_config_param(config, PLUGIN_NAME, "data_directory", self.logger)
        if data_directory is None:
            return

        address = config_utils.get_config_param(config, PLUGIN_NAME, "address", self.logger)
        if address is None:
            return

        port = config_utils.get_config_param(config, PLUGIN_NAME, "port", self.logger)
        if port is None:
            return
        
        self.zones = []
        zone_names = []
        
        for zone in range(self.num_zones):
            zone_index = "zone_" + str(zone)
            
            if zone_index not in config.options(PLUGIN_NAME):
                print zone_index + " property missing from " + PLUGIN_NAME + " section"
                return
                
            self.zones.append({ 'last': time.localtime(),
                                'state': CLOSED,
                                'name': config.get(PLUGIN_NAME, zone_index)})
            
            zone_names.append(config.get(PLUGIN_NAME, zone_index))

        if "collect_period" not in config.options(PLUGIN_NAME):
            self.collect_period = 10
        else:
            self.collect_period = float(config.get(PLUGIN_NAME, "collect_period", True))
        
        # Setup data data_logger
        self.data_logger = presence_logger.PresenceLogger(data_directory, "security", zone_names)
        
        # Setup UDP interface
        self.udp = udp_interface.UDPSocket(address, port, port, PLUGIN_NAME + "_inf")
        if not self.udp.is_initialized():
            return
        self.udp.start()
        
        self.security_state = SecurityState(object_group=self.og,
                                            logger=self.logger,
                                            breach_number=self.breach_number)
        
        self.sensor_states = ""
        self._initialized = True
    
    @staticmethod
    def get_template_config(config):
        config.add_section(PLUGIN_NAME)
        config.set(PLUGIN_NAME, "temp_data_dir", "data")
        config.set(PLUGIN_NAME, "data_directory", "%(temp_data_dir)s/security_data")
        config.set(PLUGIN_NAME, "breach_number", "+15551231234")
        config.set(PLUGIN_NAME, "monitor_device_name", "<particle security device name>")
        config.set(PLUGIN_NAME, "num_zones", "5")
        config.set(PLUGIN_NAME, "zone_0", "<zone 0 name>")
        config.set(PLUGIN_NAME, "zone_1", "<zone 1 name>")
        config.set(PLUGIN_NAME, "zone_2", "<zone 2 name>")
        config.set(PLUGIN_NAME, "zone_3", "<zone 3 name>")
        config.set(PLUGIN_NAME, "zone_4", "<zone 4 name>")

    def parse_alarm_control_message(self, message):
        fields = message.split(",")
        if len(fields) == 2 and fields[1] == "arm":
            self.security_state.arm_system()
        elif len(fields) == 2 and fields[1] == "disarm":
            self.security_state.disarm_system()
        else:
            self.logger.warning("Got weird message: '" + message + "'")

    def get_sensor_states(self):
        self.mutex.acquire()
        ss = self.sensor_states
        self.mutex.release()
        return ss
    
    def get_html(self):
        html = ""
        
        if self.is_initialized():

            arm_button_text = self.security_state.get_state_string()
            arm_button_color = "btn-danger"

            if arm_button_text == "DISARMED":
                arm_button_color = "btn-info"
            if arm_button_text == "ARMED":
                arm_button_color = "btn-success"
            if arm_button_text == "TRIGGERED":
                arm_button_color = "btn-warning"
            if arm_button_text == "ALARM":
                arm_button_color = "btn-danger"

            html = """
                <div id="security" class="jumbotron">
                    <div class="row">
                        <div class="col-md-12">
                            <h2>Security:</h2>
                            <button name="arm_btn" type="button" class="%s" onclick="armSystem()">%s</button>
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
            """ % (arm_button_color, arm_button_text, self.get_sensor_states())
        
        return html
    
    def get_javascript(self):
        jscript = ""
        
        if self.is_initialized():
            jscript = """
                function drawSecurityData()
                {
                    %s
                }
                ready_function_array.push( drawSecurityData )


                function armSystem()
                {
                    var command = "";
                    var btn = $("button[name='arm_btn']")

                    // If it is not disarmed, send a disarm command
                    if ( ! btn.hasClass("btn-info") )
                    {
                        command = "disarm"
                    }

                    // Otherwise send an arm command
                    else
                    {
                        command = "arm"
                    }

                    $.get("cgi-bin/web_control.py?set_alarm="+command, function (result)
                    {
                        var btn = $("button[name='arm_btn']")

                        if (result.trim() == "ARMED")
                        {
                            btn.removeClass();
                            btn.addClass('btn-success');
                        }
                        else if (result.trim() == "DISARMED")
                        {
                            btn.removeClass();
                            btn.addClass('btn-info');
                        }
                        else
                        {
                            btn.toggleClass('btn-primary');
                            btn.toggleClass('btn-danger');
                            alert(result);
                            setTimeout(function()
                            {
                                btn.toggleClass('btn-danger');
                                btn.toggleClass('btn-primary');
                            }, 5000);
                        }
                    });
                }
                
            """ % self.data_logger.get_google_timeline_javascript("Security State",
                                                                  "Zone",
                                                                  "security_chart_div",
                                                                  "height: 340")
        
        return jscript
    
    def private_run(self):
        self.logger.info( "Waiting for message" )
        
        msg = self.udp.get( timeout = self.collect_period )
        
        #
        # Manage the security state
        #
        if self.og.user_thread.someone_is_present():
            self.security_state.clear()
            self.security_state.disarm_system()
        else:
            self.security_state.arm_system()
        
        #
        # Sound the alarm if applicable
        #
        self.security_state.sound_alarm()

        #
        # Process the message
        #
        if msg is not None:
            
            # ( ( ip_address, port ), message )
            (_, state_str) = msg
            
            if len(state_str) != self.num_zones:
                self.logger.warning("Skipping invalid message!")
                return
            
            self.logger.info("Got message: " + state_str)
            
            self.mutex.acquire()
            try:
                self.sensor_states = ""
                zones_that_are_open = []
                
                for zone in range(self.num_zones):
                    
                    state = state_str[zone]
                    
                    # Save the closed zones for logger
                    if state == OPEN:
                        zones_that_are_open.append(self.zones[zone]['name'])
                    
                    # record state changes
                    if state != self.zones[zone]['state']:
                        self.zones[zone]['state'] = state
                        self.zones[zone]['last'] = time.localtime()
                        
                        # If nobody is home and something has changed, trigger a warning
                        if not self.og.user_thread.someone_is_present():
                            self.security_state.trigger(self.zones[zone]['name'])
                        
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
                    
                    entry += '    <td>' + self.zones[zone]['name'] + '</td>\n'
                    
                    if state == CLOSED:
                        entry += "    <td>closed</td>\n"
                    else:
                        entry += "    <td>open</td>\n"
                    
                    entry += '    <td>' + time.strftime('%b %d %I:%M%p', self.zones[zone]['last']) + '</td>\n'
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
    import ConfigParser

    conf = ConfigParser.ConfigParser()

    SecurityPlugin.get_template_config(conf)

    sec = SecurityPlugin(None, conf)
    
    if not sec.is_initialized():
        print "ERROR: initialization failed"

    else:
        sec.start()
        print "Collecting data (1 minute)..."
        time.sleep(60)
        sec.stop()

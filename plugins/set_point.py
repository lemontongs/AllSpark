
import ConfigParser
import os
from threading import Lock
from utilities import config_utils
from utilities.plugin import Plugin

PLUGIN_NAME = "set_point"


class SetPointPlugin(Plugin):

    @staticmethod
    def get_dependencies():
        return ['TemperatureMonitorPlugin']

    def __init__(self, object_group, config):
        Plugin.__init__(self, config=config, object_group=object_group, plugin_name=PLUGIN_NAME)

        self.set_point_lock = Lock()

        if not self.is_enabled():
            return

        self.set_point_filename = config_utils.get_config_param(config, PLUGIN_NAME, "set_point_file", self.logger)
        if self.set_point_filename is None:
            return

        # Create the set point file if it does not yet exist
        self.set_point_config = ConfigParser.ConfigParser()
        self.set_point_section = 'set_points'
        self.user_rule_section = 'rules'

        self.zones = {}
        self.rules = {}

        # Load and verify the set point file.
        self.load_set_point_file()
        
        self._initialized = True
    
    @staticmethod
    def get_template_config(config):
        config.add_section(PLUGIN_NAME)
        config.set(PLUGIN_NAME, "data_directory", "data")
        config.set(PLUGIN_NAME, "set_point_file", "%(data_directory)s/set_points.cfg")
        
    def load_set_point_file(self):
        
        # If the file does not exist, create it
        if not os.path.exists(self.set_point_filename):
            self.set_point_config.add_section(self.set_point_section)
            self.set_point_config.add_section(self.user_rule_section)
            
            for device in self.og.thermostat_plugin.get_device_names():
                self.set_point_config.set(self.set_point_section, device, "65.0")
            
        else:
            self.set_point_config.read(self.set_point_filename)
            
            if not self.set_point_config.has_section(self.set_point_section):
                self.set_point_config.add_section(self.set_point_section)
            
            for device in self.og.thermostat_plugin.get_device_names():
            
                if not self.set_point_config.has_option(self.set_point_section, device):
                    self.set_point_config.set(self.set_point_section, device, "65.0")
                
        # verify the contents of the file, and create the zones structure
        self.zones = {}
        for device in self.og.thermostat_plugin.get_device_names():
            
            t = 65.0
            try:
                t = float(self.set_point_config.get(self.set_point_section, device, True))
            except ValueError:
                pass
            
            if 50 > t or t > 90:
                self.logger.warning( "set point for '" + device + "' is out of bounds (<50 or >90). Got: " + str(t) +
                                     ". Setting it to 65.0" )
                t = 65.0
            
            self.zones[device] = { 'set_point': t }
            self.set_point_config.set(self.set_point_section, device, t)

        # Write the file, with the corrections (if any)
        self.save_zones_to_file()
        
        # Load the rules
        self.rules = {'away_set_point': 60.0, 'rules': {} }
        
        for option in self.set_point_config.options(self.user_rule_section):
            if 'away_set_point' in option:
                try:
                    self.rules['away_set_point'] = \
                        float(self.set_point_config.get(self.user_rule_section, 'away_set_point', True))
                except ValueError:
                    pass
            else:
                self.rules['rules'][option] = \
                    self.set_point_config.get(self.user_rule_section, option, True)

    def save_zones_to_file(self):
        for device in self.zones.keys():
            set_point = str(self.zones[device]['set_point'])
            self.set_point_config.set(self.set_point_section, device, set_point)
        
        with open(self.set_point_filename, 'wb') as configfile:
            self.set_point_config.write(configfile)

    # Get the set point, this can be different if the user is not home
    def get_set_point(self, zone_name):
        if self._initialized:
            
            self.set_point_lock.acquire()
            
            if zone_name not in self.zones.keys():
                self.logger.warning( "Warning: get_set_point: " + zone_name + " not found" )
                return 60.0
            
            set_point = self.rules['away_set_point']
            
            # if any of the users are home AND have this zone in there list, 
            # use the custom set point (from the set point file)
            for user in self.rules['rules']:
                if self.og.user_thread.is_user_home(user) and (zone_name in self.rules['rules'][user]):
                    set_point = self.zones[zone_name]['set_point']
                    break
            
            # None of the users who are home have this zone in there rules so 
            # use the "away" set point
            self.set_point_lock.release()
            return set_point
        
    def parse_set_point_message(self, msg):
        if len(msg.split(',')) != 3:
            self.logger.warning( "Error parsing set_point message" )
            return
        
        self.logger.debug("Got message: " + msg)
        
        zone = msg.split(',')[1]
        
        self.set_point_lock.acquire()
        try:
            if zone not in self.zones.keys():
                self.logger.warning( "Error parsing set_point message: " + zone + " not found" )
                self.set_point_lock.release()
                return
                
            set_point = 65.0
            try:
                set_point = float(msg.split(',')[2])
            except ValueError:
                pass
            
            self.logger.debug("Set point for: " + zone + " changed to: " + str(set_point) )
            
            self.zones[zone]['set_point'] = set_point
            self.save_zones_to_file()
        except:
            self.set_point_lock.release()
            raise

        self.set_point_lock.release()

    def get_html(self):

        html = ""

        if self.is_initialized():

            html = '<div id="thermostats" class="jumbotron">'

            for zone in self.zones:

                zone_name       = zone.replace("_floor_temp", "")
                zone_name_upper = zone_name[0].upper() + zone_name[1:]

                html += """

                <div class="row">
                    <div class="col-md-2">
                        <h2>%s Floor</h2>          <!-- FLOOR NAME -->
                        <p>Current: %.1f</p>       <!-- TOP CURRENT TEMP -->
                    </div>
                    <div class="col-md-5">
                        <h2></h2>
                        <div class="input-group input-group-lg">                           <!-- ZONE NAME, SET POINT -->
                            <input type="text" class="form-control" name="%s" value="%.1f">
                            <div class="input-group-btn">
                                <button name="%s"
                                        type="button"
                                        class="btn btn-primary"
                                        onclick="updateSetPoint('%s')">Submit</button>
                            </div>
                        </div>
                        <script>
                            $("input[name='%s']").TouchSpin({
                                min: 50,
                                max: 80,
                                step: 0.5,
                                decimals: 1,
                                boostat: 5,
                                maxboostedstep: 10,
                                prefix: "Set:",
                                postfix: 'F'
                            });
                        </script>
                    </div>
                </div>

                """ % ( zone_name_upper,
                        self.og.thermostat_plugin.get_current_device_temp( zone ),
                        zone,
                        self.get_set_point( zone ),
                        zone + "_btn",
                        zone,
                        zone )

            html += '</div>'
        
        return html

    @staticmethod
    def get_javascript():

        jscript = """

        function updateSetPoint(device)
        {
            var set_point = $("input[name='"+device+"']").val()

            $.get("cgi-bin/web_control.py?set_temp="+set_point+"&floor="+device, function (result)
            {
                if (result.trim() == "OK")
                {
                    $("button[name='"+device+"_btn']").toggleClass('btn-primary');
                    $("button[name='"+device+"_btn']").toggleClass('btn-success');
                    setTimeout(function()
                    {
                        $("button[name='"+device+"_btn']").toggleClass('btn-success');
                        $("button[name='"+device+"_btn']").toggleClass('btn-primary');
                    }, 5000);
                }
                else
                {
                    $("button[name='"+device+"_btn']").toggleClass('btn-primary');
                    $("button[name='"+device+"_btn']").toggleClass('btn-danger');
                    alert(result);
                    setTimeout(function()
                    {
                        $("button[name='"+device+"_btn']").toggleClass('btn-danger');
                        $("button[name='"+device+"_btn']").toggleClass('btn-primary');
                    }, 5000);
                }
            });
        }

        """

        return jscript

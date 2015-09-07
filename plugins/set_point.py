
import ConfigParser
import os
from threading import Lock


class Set_Point():
    def __init__(self, object_group, config):
        self.og = object_group
        self.initialized = False
        self.set_point_lock = Lock()
        
        config_sec = "set_point"

        if config_sec not in config.sections():
            print config_sec + " section missing from config file"
            return

        if "set_point_file" not in config.options(config_sec):
            print "set_point_file property missing from " + config_sec + " section"
            return
        self.set_point_filename = config.get(config_sec, "set_point_file")
        
        # Create the set point file if it does not yet exist
        self.set_point_config = ConfigParser.ConfigParser()
        self.set_point_section = 'set_points'
        self.user_rule_section = 'rules'
        
        # Load and verify the set point file.
        self.load_set_point_file()
        
        self.initialized = True
    
    def load_set_point_file(self):
        
        # If the file does not exist, create it
        if not os.path.exists(self.set_point_filename):
            self.set_point_config.add_section(self.set_point_section)
            self.set_point_config.add_section(self.user_rule_section)
            
            for device in self.og.thermostat.getDeviceNames():
                self.set_point_config.set(self.set_point_section, device, "65.0")
            
        else:
            self.set_point_config.read(self.set_point_filename)
            
            if not self.set_point_config.has_section(self.set_point_section):
                self.set_point_config.add_section(self.set_point_section)
            
            for device in self.og.thermostat.getDeviceNames():
            
                if not self.set_point_config.has_option(self.set_point_section, device):
                    self.set_point_config.set(self.set_point_section, device, "65.0")
                
        # verify the contents of the file, and create the zones structure
        self.zones = {}
        for device in self.og.thermostat.getDeviceNames():
            
            t = 65.0
            try:
                t = float(self.set_point_config.get(self.set_point_section, device, True))
            except:
                pass
            
            if 50 > t or t > 90:
                print "WARNING: set point for '" + device + "' is out of bounds (<50 or >90). Got: " + str(t) + ". Setting it to 65.0"
                t = 65.0
            
            self.zones[device] = {'set_point':t}
            self.set_point_config.set(self.set_point_section, device, t)
            
        
        # Write the file, with the corrections (if any)
        self.save_zones_to_file()
        
        # Load the rules
        self.rules = {'away_set_point' : 60.0, 'rules' : {} }
        
        for option in self.set_point_config.options(self.user_rule_section):
            if 'away_set_point' in option:
                try:
                    self.rules['away_set_point'] = \
                        float(self.set_point_config.get(self.user_rule_section, 'away_set_point', True))
                except:
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
        if self.initialized:
            
            self.set_point_lock.acquire()
            
            if zone_name not in self.zones.keys():
                print "Warning: get_set_point:", zone_name, "not found"
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
            print "Error parsing set_point message"
            return
        
        zone = msg.split(',')[1]
        
        self.set_point_lock.acquire()
        try:
            if zone not in self.zones.keys():
                print "Error parsing set_point message: "+zone+" not found"
                self.set_point_lock.release()
                return
                
            set_point = 65.0
            try:
                set_point = float(msg.split(',')[2])
            except:
                pass
            
            self.zones[zone]['set_point'] = set_point
            self.save_zones_to_file()
        except:
            self.set_point_lock.release()
            raise

        self.set_point_lock.release()

    def isInitialized(self):
        return self.initialized
    
    def get_html(self):
        html = '<div id="thermostats" class="jumbotron">'
        
        for zone in self.zones:
            
            html += """
            
            <div class="row">
                <div class="col-md-2">
                    <h2>%s Floor</h2>          <!-- FLOOR NAME -->
                    <p>Current: %.1f</p>       <!-- TOP CURRENT TEMP -->
                </div>
                <div class="col-md-5">
                    <h2></h2>
                    <div class="input-group input-group-lg">
                        <input id="demo5" type="text" class="form-control" name="%s" value="%.1f">   <!-- ZONE NAME, SET POINT -->
                        <div class="input-group-btn">
                            <button name="%s" type="button" class="btn btn-primary" onclick="updateSetPoint('%s')">Submit</button>
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
            
            """ % ( zone.replace("_floor_temps",""), \
                    self.og.thermostat.get_current_device_temp( zone ), \
                    zone, \
                    self.get_set_point( zone ),
                    zone+"_btn", \
                    zone,
                    zone )
            
        
        html += '</div>'
        
        return html
    
    def get_javascript(self):
        jscript = """
        
        function updateSetPoint(device)
        {
            var set_point = $("input[name='"+device+"']").val()
            
            $.get("cgi-bin/set_temp.py?set_temp="+set_point+"&floor="+device, function (result)
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
    

            
            
            
            
            
            
            
            
            
            
            
            
            
            

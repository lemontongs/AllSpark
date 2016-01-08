import subprocess
import time
from utilities.thread_base import ThreadedPlugin
from utilities import config_utils
from utilities.data_logging import presence_logger

PLUGIN_NAME = "user_thread"


class UserMonitorPlugin(ThreadedPlugin):

    @staticmethod
    def get_dependencies():
        return []

    def __init__(self, object_group, config):
        ThreadedPlugin.__init__(self, config=config, object_group=object_group, plugin_name=PLUGIN_NAME)

        if not self.enabled:
            return

        self.data_directory = config_utils.get_config_param(config, PLUGIN_NAME, "data_directory", self.logger)
        if self.data_directory is None:
            return

        user_names = config_utils.get_config_param(config, PLUGIN_NAME, "users", self.logger)
        if user_names is None:
            return
        user_names = user_names.split(",")
        
        self.users = {}
        
        for user in user_names:
            if user not in config.sections():
                print user + " section is missing"
                return
            if "mac" not in config.options(user):
                print "mac property is missing from the " + user + " section"
                return
            self.users[user] = {'mac': config.get(user, "mac"),
                                'is_home': False,
                                'last_seen': 0.0}
        
        self.users_present = True
        
        self.data_logger = presence_logger.PresenceLogger(self.data_directory, "user_data", user_names)
        
        self._initialized = True
    
    @staticmethod
    def get_template_config(config):
        config.add_section(PLUGIN_NAME)
        config.set(PLUGIN_NAME, "temp_data_dir", "data")
        config.set(PLUGIN_NAME, "data_directory", "%(temp_data_dir)s/user_data")
        config.set(PLUGIN_NAME, "users", "user_1,user_2,user_3")
        config.add_section("user_1")
        config.set("user_1", "mac", "xx:xx:xx:xx:xx:xx")
        config.add_section("user_2")
        config.set("user_2", "mac", "xx:xx:xx:xx:xx:xx")
        config.add_section("user_3")
        config.set("user_3", "mac", "xx:xx:xx:xx:xx:xx")

    def private_run(self):
        
        #
        # Check if a user is here now
        #
        command = ["arp-scan", "-l", "--retry=5", "--timeout=500"]
        result = subprocess.Popen(command, stdout=subprocess.PIPE).stdout.read()
        now = time.time()
        for user in self.users.keys():
            was_home = self.users[user]['is_home']
            is_home  = self.users[user]['mac'] in result
            if is_home:
                self.users[user]['last_seen'] = now
            if (now - self.users[user]['last_seen']) < 600:
                self.users[user]['is_home'] = True
            else:
                self.users[user]['is_home'] = False
            
            # Fire off a message when a user arrives home
            if not was_home and self.users[user]['is_home']:
                self.og.broadcast.send( "user:" + user + " has arrived at home" )
        
        #
        # Process the collected data
        #
        data = []
        someone_is_home = False
        for user in self.users.keys():
            if self.users[user]['is_home']:
                data.append(user)
                someone_is_home = True
        
        self.logger.info( "Someone is home: " + str(someone_is_home) )
        self.users_present = someone_is_home
        self.data_logger.add_data( data )
            
        for _ in range(10):
            if self._running:
                time.sleep(1)
        
    def is_someone_present_string(self):
        if not self._initialized:
            return "UNKNOWN"
        if self.someone_is_present():
            return "YES"
        return "NO"
    
    def someone_is_present(self):
        if not self._initialized:
            return False
        return self.users_present
    
    def is_user_home(self, user):
        
        for case_sensitive_user in self.users:
            if case_sensitive_user.lower() == user.lower():
                return self.users[case_sensitive_user]['is_home'] 
        
        self.logger.warning( "unknown user: " + user )
        return False
    
    def get_html(self):

        html = ""

        if self.is_initialized():
            html = """
                <div id="whosehome" class="jumbotron">
                    <div class="row">
                        <div class="col-md-12">
                            <h2>Someone is home: %s</h2>     <!-- SOMEONE IS HOME -->
                            <div id="user_chart_div"></div>
                        </div>
                    </div>
                </div>
            """ % self.is_someone_present_string()
        
        return html
    
    def get_javascript(self):
        jscript = ""
        
        if self.is_initialized():
            jscript = """
                function drawUserData()
                {
                    %s
                }
                ready_function_array.push( drawUserData )
                
            """ % self.data_logger.get_google_timeline_javascript("User State", "User", "user_chart_div")
        
        return jscript

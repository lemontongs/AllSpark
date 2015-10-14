import csv
import subprocess
import time
import datetime
import logging
from threading import Lock
from utilities import thread_base
from utilities import config_utils

#
# Example usage:
#
#  t = user_thread.User_Thread(filename = "user_state.csv", 
#                              users = [("Matt","xx:xx:xx:xx:xx:xx")])
#  if t.isInitialized():
#    t1.start()
#

CONFIG_SEC_NAME = "user_thread"

logger = logging.getLogger('allspark.' + CONFIG_SEC_NAME)

class User_Thread(thread_base.AS_Thread):
    def __init__(self, object_group, config):
        thread_base.AS_Thread.__init__(self, CONFIG_SEC_NAME)
        
        self.og = object_group
        
        if not config_utils.check_config_section( config, CONFIG_SEC_NAME ):
            return

        self.filename = config_utils.get_config_param( config, CONFIG_SEC_NAME, "data_file")
        if self.filename == None:
            return

        usernames = config_utils.get_config_param( config, CONFIG_SEC_NAME, "users")
        if usernames == None:
            return
        usernames = usernames.split(",")
        
        self.users = {}
        
        for user in usernames:
            if user not in config.sections():
                print user + " section is missing"
                return
            if "mac" not in config.options(user):
                print "mac property is missing from the " + user + " section"
                return
            self.users[user] = {'mac':config.get(user, "mac"), 'is_home':False, 'last_seen':0.0}
        
        self.mutex = Lock()
        
        self.users_present = True
        try:
            self.file_handle = open(self.filename, 'a+')
            self.file_handle.seek(0,2)
        except Exception as e:
            logger.error( "Failed to open " + self.filename + ":" + str( e ) )
            return
        
        self._initialized = True
    
    @staticmethod
    def get_template_config(config):
        config.add_section(CONFIG_SEC_NAME)
        config.set(CONFIG_SEC_NAME,"data_directory", "data")
        config.set(CONFIG_SEC_NAME, "data_file", "%(data_directory)s/user_state.csv")
        config.set(CONFIG_SEC_NAME, "users", "user_1,user_2,user_3")
        config.add_section("user_1")
        config.set("user_1","mac", "xx:xx:xx:xx:xx:xx")
        config.add_section("user_2")
        config.set("user_2","mac", "xx:xx:xx:xx:xx:xx")
        config.add_section("user_3")
        config.set("user_3","mac", "xx:xx:xx:xx:xx:xx")

    def private_run(self):
        
        #
        # Check if a user is here now
        #
        command = ["arp-scan","-l","--retry=5","--timeout=500"]
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
                self.og.broadcast.send( user+" has arrived at home" )
        
        #
        # Write the collected data to file
        #
        self.mutex.acquire()
        self.file_handle.write(str(time.time()))
        someone_is_home = False
        for user in self.users.keys():
            if self.users[user]['is_home']:
                self.file_handle.write(","+user)
                someone_is_home = True
        self.users_present = someone_is_home
        self.file_handle.write("\n")
        self.file_handle.flush()
        self.mutex.release()
            
        for _ in range(10):
            if self._running:
                time.sleep(1)
                        
        logger.info( "Thread stopped" )
        
    def private_run_cleanup(self):
        self.file_handle.close()
    
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
        
        logger.warning( "Warning: unknown user: "+user )
        return False
    
    def get_html(self):
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
        jscript = """
            function drawUserData() {
                var dataTable = new google.visualization.DataTable();

                dataTable.addColumn({ type: 'string', id: 'User' });
                dataTable.addColumn({ type: 'date', id: 'Start' });
                dataTable.addColumn({ type: 'date', id: 'End' });

                dataTable.addRows([
                  
                %s

                ]);

                chart = new google.visualization.Timeline(document.getElementById('user_chart_div'));
                chart.draw(dataTable);
            }
            ready_function_array.push( drawUserData )
            
            """ % self.get_history()
        
        return jscript
        
    def get_history(self, days=1, seconds=0):
        
        # start_time is "now" minus days and seconds
        # only this much data willl be shown
        start_time = datetime.datetime.now() - datetime.timedelta(days,seconds)
        
        # Load the data from the file
        self.mutex.acquire()
        file_handle = open(self.filename, 'r')
        csvreader = csv.reader(file_handle)
        lines = 0
        userdata = []
        for row in csvreader:
            userdata.append(row)
            lines += 1
        self.mutex.release()
        
        # Build the return string
        return_string = ""
        
        # Skip the ones before the start_time
        start_index = len(userdata)
        for i, row in enumerate(userdata):
            dt = datetime.datetime.fromtimestamp(float(row[0]))
            if dt > start_time:
                start_index = i
                break
        
        # Process the remaining data into a usable structure
        processed_data = []
        for i, row in enumerate(userdata[start_index:]):
            
            dt = datetime.datetime.fromtimestamp(float(row[0]))
            
            year   = dt.strftime('%Y')
            month  = str(int(dt.strftime('%m')) - 1) # javascript expects month in 0-11, strftime gives 1-12 
            day    = dt.strftime('%d')
            hour   = dt.strftime('%H')
            minute = dt.strftime('%M')
            second = dt.strftime('%S')
            
            time = 'new Date(%s,%s,%s,%s,%s,%s)' % (year,month,day,hour,minute,second)
            
            temp = {}
            temp["time"] = time
            for user in self.users:
                if user in row:
                    temp[user] = "1"
            
            processed_data.append( temp )
        
        if len(processed_data) == 0:
            return "[] // None available"
        
        # Save the first state
        start_times = {} 
        for user in self.users:
            if user in processed_data[0]:
                start_times[user] = processed_data[0]["time"]
            else:
                start_times[user] = None
        
        # Go through the processed data and write out a string whenever the user
        # is no longer present.
        for i, row in enumerate(processed_data[1:]):
            for user in self.users:
                if start_times[user] == None and (user in row):
                    start_times[user] = processed_data[i]["time"]
                if start_times[user] != None and (not (user in row)):
                    # write a string
                    return_string += ("['%s',  %s, %s],\n" % (user,  \
                                                              start_times[user],  \
                                                              row["time"]))
                    # set start time to None
                    start_times[user] = None
        
        for user in self.users:
            if start_times[user] != None:
                return_string += ("['%s',  %s, %s],\n" % (user,  \
                                                          start_times[user],  \
                                                          processed_data[-1]["time"]))
        # Remove the trailing comma and return line    
        if len(return_string) > 2:
            return_string = return_string[:-2]
        
        return return_string

if __name__ == "__main__":
    
    user = User_Thread(filename = "user_state.csv", users = [("Matt","xx:xx:xx:xx:xx:xx")])

    print user.get_history()



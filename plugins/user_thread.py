import csv
import subprocess
import sys
import time
import datetime
import os
from threading import Thread, Lock


#
# Example usage:
#
#  t = user_thread.User_Thread(filename = "user_state.csv", 
#                              users = [("Matt","xx:xx:xx:xx:xx:xx")])
#  if t.isInitialized():
#    t1.start()
#

class User_Thread(Thread):
    def __init__(self, object_group, config):
        Thread.__init__(self)
        self.og = object_group
        self.initialized = False
        
        config_sec = "user_thread"
        
        if config_sec not in config.sections():
            print config_sec + " section missing from config file"
            return
        
        if "data_file" not in config.options(config_sec):
            print "data_file property missing from " + config_sec + " section"
            return

        self.filename = config.get(config_sec, "data_file")
        
        if "users" not in config.options(config_sec):
            print "users property missing from " + config_sec + " section"
            return
        
        usernames = config.get(config_sec, "users").split(",")
        
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
        self.running = False
        self.users_present = True
        try:
            self.file_handle = open(self.filename, 'a+')
            self.file_handle.seek(0,2)
        except:
            print "Failed to open", self.filename, ":", sys.exc_info()[1]
            return
        
        self.initialized = True
        
    def isInitialized(self):
        return self.initialized
    
    def run(self):
        
        if not self.initialized:
            print "Warning: start called before initialized, not running"
            return
        
        if os.geteuid() != 0:
            print "ERROR: Running in non-privaleged mode, User_Thread not running" 
            return
        
        
        #############
        # MAIN LOOP #
        #############
        self.running = True
        while self.running:
          
            #
            # Check if a user is here now
            #
            result = subprocess.Popen(["arp-scan","-l"], stdout=subprocess.PIPE).stdout.read()
            now = time.time()
            for user in self.users.keys():
                is_home = self.users[user]['mac'] in result
                if is_home:
                    self.users[user]['last_seen'] = now
                if (now - self.users[user]['last_seen']) < 600:
                    self.users[user]['is_home'] = True
                else:
                    self.users[user]['is_home'] = False
            
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
            
            for _ in range(60):
                if self.running:
                    time.sleep(1)
  
    def stop(self):
        self.running = False
        self.file_handle.close()
    
    def is_someone_present_string(self):
        if not self.initialized:
            return "UNKNOWN"
        if self.someone_is_present():
            return "YES"
        return "NO"
    
    def someone_is_present(self):
        if not self.initialized:
            return False
        return self.users_present
    
    def is_user_home(self, user):
        
        for case_sensitive_user in self.users:
            if case_sensitive_user.lower() == user.lower():
                return self.users[case_sensitive_user]['is_home'] 
        
        print "Warning: unknown user: "+user
        return False
    
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
    
    user = User_Thread(filename = "user_state.csv", 
                       users = [("Matt","xx:xx:xx:xx:xx:xx")])


    print user.get_history()



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
    def __init__(self, config):
        Thread.__init__(self)
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
        
        self.users = []
        
        for user in usernames:
            if user not in config.sections():
                print user + " section is missing"
                return
            if "mac" not in config.options(user):
                print "mac property is missing from the " + user + " section"
                return
            self.users.append((user,config.get(user, "mac")))
        
        self.mutex = Lock()
        self.running = False
        self.someone_is_home = True
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
        
        # Keep track of the last time a user was seen
        last_seen = {}
        for (user,mac_addr) in self.users:
            last_seen[user] = 0.0
        
        #############
        # MAIN LOOP #
        #############
        self.running = True
        while self.running:
          
            #
            # Check if a user is here now
            #
            result = subprocess.Popen(["arp-scan","-l"], stdout=subprocess.PIPE).stdout.read()
            t = {}
            someone_is_home = False
            for (user,mac_addr) in self.users:
                t[user] = False
                if mac_addr in result:
                    last_seen[user] = time.time()
                    t[user] = True
                    someone_is_home = True
            
            self.someone_is_home = someone_is_home
            
            #
            # Write the collected data to file
            #
            self.mutex.acquire()
            self.file_handle.write(str(time.time()))
            for (user,mac) in self.users:
                if (time.time() - last_seen[user]) < 600:
                    self.file_handle.write(","+user)
            self.file_handle.write("\n")
            self.file_handle.flush()
            self.mutex.release()
            
            time.sleep(30)
  
    def stop(self):
        self.running = False
        self.file_handle.close()
    
    def get_is_someone_home(self):
        if self.someone_is_home:
            return "YES"
        return "NO"
    
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
            for (j,(user,mac)) in enumerate(self.users):
                if user in row:
                    temp[user] = "1"
            
            processed_data.append( temp )
        
        if len(processed_data) == 0:
            return "[] // None available"
        
        # Save the first state
        previous = processed_data[0]
        start_times = {} 
        for (user,mac) in self.users:
            if user in processed_data[0]:
                start_times[user] = processed_data[0]["time"]
            else:
                start_times[user] = None
        
        # Go through the processed data and write out a string whenever the user
        # is no longer present.
        for i, row in enumerate(processed_data[1:]):
            for (user,mac) in self.users:
                if start_times[user] == None and (user in row):
                    start_times[user] = processed_data[i]["time"]
                if start_times[user] != None and (not (user in row)):
                    # write a string
                    return_string += ("['%s',  %s, %s],\n" % (user,  \
                                                              start_times[user],  \
                                                              row["time"]))
                    # set start time to None
                    start_times[user] = None
        
        for (user,mac) in self.users:
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



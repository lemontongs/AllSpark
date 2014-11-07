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
#  t1 = user_thread.User_Thread(filename = "user_state.csv", 
#                               users = [("Matt","bc:f5:ac:f4:35:95"),
#                                        ("Kat", "bc:f5:ac:f4:35:95"),
#                                        ("Adam","bc:f5:ac:f4:35:95")])
#  if t1 != None:
#    t1.start()
#

class User_Thread(Thread):
    def __init__(self, filename, users):
        Thread.__init__(self)
        
        self.mutex = Lock()
        self.running = False
        self.filename = filename
        self.users = users
        self.is_someone_home = True
        try:
            self.file_handle = open(self.filename, 'r+')
        except:
            print "Failed to open", self.filename, ":", sys.exc_info()[1]
        
        self.file_handle.seek(0,2)
        
    def run(self):
    
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
            for (user,mac_addr) in self.users:
                t[user] = False
                if mac_addr in result:
                    last_seen[user] = time.time()
                    t[user] = True

            #
            # Check if a user has been seen in the last 10 minutes
            #
            self.is_someone_home = False
            for (user,mac_addr) in self.users:
                if (time.time() - last_seen[user]) < 600:
                    self.is_someone_home = True

            #
            # Write the collected data to file
            #
            self.mutex.acquire()
            self.file_handle.write(str(time.time()))
            for (user,mac) in self.users:
                if (user in t) and t[user]:
                    self.file_handle.write(",1")
                else:
                    self.file_handle.write(",0")
            self.file_handle.write("\n")
            self.file_handle.flush()
            self.mutex.release()
            time.sleep(10)
  
    def stop(self):
        self.running = False
        self.file_handle.close()
    
    def get_is_someone_home(self):
        if self.is_someone_home:
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
        for i, row in enumerate(userdata):
            
            # Skip the ones before the start_time
            dt = datetime.datetime.fromtimestamp(float(row[0]))
            if dt < start_time:
                continue
            
            year   = dt.strftime('%Y')
            month  = str(int(dt.strftime('%m')) + 1) // javascript expects month in 0-11, strftime gives 1-12 
            day    = dt.strftime('%d')
            hour   = dt.strftime('%H')
            minute = dt.strftime('%M')
            second = dt.strftime('%S')
            
            time = 'new Date(%s,%s,%s,%s,%s,%s)' % (year,month,day,hour,minute,second)
            
            # Print a line each time a user is seen
            rownum = 0
            for (user,mac) in self.users:
                rownum = rownum + 1
                if row[rownum] == "1":
                    return_string += ("        ['%s',  %s, %s],\n" % (user,time,time))
        
        if len(return_string) > 2:
            return_string = return_string[:-2]
        
        return return_string
            
            
            
            
            
            
            
            
            
            
            
            
            
            

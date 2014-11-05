#! /usr/bin/python

import errno
import os
import sys
import time
import temperature_thread
import user_thread

DEBUG = False

def build_html_file(filename, thermostat, user_thread):

    if DEBUG:
        print "building file"
    
    f = open("thermostat_template.html", "r")
    content = f.read()
    f.close()
    
    content = content % (thermostat.get_history(),  \
                         user_thread.get_history(), \
                         thermostat.get_temp(),     \
                         user_thread.get_is_someone_home())
    
    
    if DEBUG:
        print "writing file"
    
    remove_file(filename)
    f = open(filename, "w+")
    f.write(content)
    f.close()
    
def remove_file(filename):
    try:
        os.remove(filename)
    except OSError as f:    # its OK if the file does not exist
        pass

def check_permissions(filename):
    try:
        remove_file(filename)
        f = open(filename, "w+")
        f.close()
    except:
        print "check_permissions() got error:", sys.exc_info()
        sys.exit(1)

################################################################################
#
#  MAIN
#
################################################################################
if __name__ == '__main__':
    
    filename = "/var/www/thermostat.html"
    
    if len(sys.argv) == 2:
        if "-h" == sys.argv[1]:
            print "Usage: python %s [html output file]" % sys.argv[0]
            os._exit(0)
        
        filename = sys.argv[1]
    
    
    check_permissions(filename)
    
    ############################################################################
    # Thermostat Threat
    ############################################################################
    thermostat1 = \
        temperature_thread.Temperature_Thread(filename="floor_temps.csv", 
                                              device_names=["main_floor_temp",
                                                            "top_floor_temp",
                                                            "basement_floor_temp"])
    if thermostat1 == None:
        print "Error creating temperature thread"
        sys.exit(1)
    
    thermostat1.start()

    ############################################################################
    # User Threat
    ############################################################################
    user1 = \
        user_thread.User_Thread(filename = "user_state.csv", 
                                users = [("Matt","bc:f5:ac:f4:35:95"),
                                         ("Kat", "58:a2:b5:e9:2b:fc"),
                                         ("Adam","24:e3:14:d2:f8:b2")])
    if user1 == None:
        print "Error creating user thread"
        thermostat1.stop()
        sys.exit(1)
    
    user1.start()
    
    ############################################################################
    # Main loop
    ############################################################################
    while True:
        try:
            build_html_file(filename, thermostat1, user1)
            os.system("/home/mlamonta/bin/blink1-tool -q --hsb=130,200,50")
            time.sleep(60)
            os.system("/home/mlamonta/bin/blink1-tool -q --off")
        except KeyboardInterrupt:
            thermostat1.stop()
            user1.stop()
            os._exit(0)
        






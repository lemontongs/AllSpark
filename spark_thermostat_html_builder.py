#! /usr/bin/python

import errno
import os
import sys
import time
import temperature_thread
import user_thread

DEBUG = False

template_contents = None

def build_html_file(filename, thermostat, user_thread):
    global template_contents
    
    if DEBUG:
        print "building file"
    
    if template_contents == None:
        f = open("thermostat_template.html", "r")
        template_contents = f.read()
        f.close()
    
    content = template_contents % (thermostat.get_history(),  \
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
    
    #filename = "/var/www/control/index.html"
    filename = "data/index.html"
    
    if len(sys.argv) == 2:
        if "-h" == sys.argv[1]:
            print "Usage: python %s [html output file]" % sys.argv[0]
            os._exit(0)
        
        filename = sys.argv[1]
    
    
    check_permissions(filename)
    
    if not os.path.exists("data"):
        os.makedirs("data")
    
    ############################################################################
    # Thermostat Thread
    ############################################################################
    thermostat = \
        temperature_thread.Temperature_Thread(filename="data/floor_temps.csv", 
                                              device_names=["main_floor_temp",
                                                            "top_floor_temp",
                                                            "basement_floor_temp"])
    if not thermostat.isInitialized():
        print "Error creating temperature thread"
        sys.exit(1)
    
    thermostat.start()

    ############################################################################
    # User Thread
    ############################################################################
    user = \
        user_thread.User_Thread(filename = "data/user_state.csv", 
                                users = [("Matt","bc:f5:ac:f4:35:95"),
                                         ("Kat", "58:a2:b5:e9:2b:fc"),
                                         ("Adam","24:e3:14:d2:f8:b2")])
    if not user.isInitialized():
        print "Error creating user thread"
        thermostat.stop()
        sys.exit(1)
    
    user.start()
    
    ############################################################################
    # Main loop
    ############################################################################
    while True:
        try:
            build_html_file(filename, thermostat, user)
            os.system("/home/mlamonta/bin/blink1-tool -q --hsb=130,200,50")
            time.sleep(60)
            os.system("/home/mlamonta/bin/blink1-tool -q --off")
        except KeyboardInterrupt:
            thermostat.stop()
            user.stop()
            os._exit(0)
        






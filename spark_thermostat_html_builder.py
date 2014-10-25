#! /usr/bin/python

import errno
import os
import sys
import time
import temperature_thread

DEBUG = False

def build_html_file(filename, thermostat):

    if DEBUG:
        print "building file"
    
    f = open("thermostat_template.html", "r")
    content = f.read()
    f.close()
    
    content = content % (thermostat.get_history(), thermostat.get_temp())
    
    
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
    
    check_permissions(filename)
    
    thermostat1 = \
        temperature_thread.Temperature_Thread(filename="/home/mlamonta/thermostat/floor_temps.csv", 
                                              device_names=["main_floor_temp",
                                                            "top_floor_temp",
                                                            "basement_floor_temp"])
    if thermostat1 == None:
        print "Error creating thread"
        sys.exit(1)
    
    thermostat1.start()

    while True:
        try:
            build_html_file(filename, thermostat1)
            os.system("/home/mlamonta/bin/blink1-tool -q --hsb=130,200,50")
            time.sleep(60)
            os.system("/home/mlamonta/bin/blink1-tool -q --off")
        except KeyboardInterrupt:
            thermostat1.stop()
            os._exit(0)
        






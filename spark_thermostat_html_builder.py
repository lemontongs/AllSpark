#! /usr/bin/python

import errno
import os
import sys
import signal
import time
import comms_thread
import temperature_thread
import user_thread
import memory_thread
import furnace_control

DEBUG = False

template_contents = None

initial_set_point = 70.0

users = [("Matt","bc:f5:ac:f4:35:95"),
         ("Kat", "58:a2:b5:e9:2b:fc"),
         ("Adam","24:e3:14:d2:f8:b2")]

devices = ["top_floor_temp","main_floor_temp","basement_floor_temp"]

######################################################################
# Functions
######################################################################

def build_html_file(filename, thermostat, user_thread):
    global template_contents
    
    if DEBUG:
        print "building file"
    
    if template_contents == None:
        f = open("thermostat_template.html", "r")
        template_contents = f.read()
        f.close()
    
    content = template_contents % (user_thread.get_history(), \
                                   thermostat.get_average_temp(), \
                                   thermostat.get_current_device_temp(devices[0]), \
                                   furnace_ctrl.get_set_point(devices[0]), \
                                   thermostat.get_current_device_temp(devices[1]), \
                                   furnace_ctrl.get_set_point(devices[1]), \
                                   thermostat.get_current_device_temp(devices[2]), \
                                   furnace_ctrl.get_set_point(devices[2]), \
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
                                              device_names=devices)
    if not thermostat.isInitialized():
        print "Error creating temperature thread"
        sys.exit(1)
    
    thermostat.start()

    ############################################################################
    # User Thread
    ############################################################################
    user = \
        user_thread.User_Thread(filename = "data/user_state.csv", users = users)
    
    if not user.isInitialized():
        print "Error creating user thread"
        thermostat.stop()
        sys.exit(1)
    
    user.start()
    
    ############################################################################
    # Memory Thread
    ############################################################################
    mem = memory_thread.Memory_Thread(filename = "data/mem_usage.csv")
    
    if not mem.isInitialized():
        print "Error creating memory thread"
        thermostat.stop()
        user.stop()
        sys.exit(1)
    
    mem.start()
    
    ############################################################################
    # Furnace Control Thread
    ############################################################################
    
    def top_temp():
        return thermostat.get_current_device_temp(devices[0])
    def main_temp():
        return thermostat.get_current_device_temp(devices[1])
    def basement_temp():
        return thermostat.get_current_device_temp(devices[2])
    
    zones = [ {'name':devices[0], 'pin':18, 'get_temp':top_temp},
              {'name':devices[1], 'pin':23, 'get_temp':main_temp},
              {'name':devices[2], 'pin':24, 'get_temp':basement_temp} ]

    furnace_ctrl = furnace_control.Furnace_Control(zones)

    if not furnace_ctrl.isInitialized():
        print "Error creating furnace controller"
        thermostat.stop()
        user.stop()
        mem.stop()
        sys.exit(1)
    
    # Default all device sety points to the same
    for device in devices:
        furnace_ctrl.set_point(device, initial_set_point)
    
    furnace_ctrl.start()

    ############################################################################
    # Comms Thread
    ############################################################################
    
    comms = comms_thread.Comms_Thread()

    if not comms.isInitialized():
        print "Error creating comms thread"
        thermostat.stop()
        user.stop()
        mem.stop()
        furnace_ctrl.stop()
        sys.exit(1)

    comms.register_callback("set_point", furnace_ctrl.parse_set_point_message)
    comms.start()
    
    
    ############################################################################
    # Main loop
    ############################################################################
    
    def receive_signal(signum, stack):
        print "Caught signal:", str(signum)
        thermostat.stop()
        user.stop()
        mem.stop()
        furnace_ctrl.stop()
        os._exit(0)

    signal.signal(signal.SIGINT, receive_signal)
    
    while True:
        build_html_file(filename, thermostat, user)
        #os.system("/home/mlamonta/bin/blink1-tool -q --hsb=130,200,50")
        time.sleep(60)
        #os.system("/home/mlamonta/bin/blink1-tool -q --off")
        






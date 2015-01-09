#! /usr/bin/python

import ConfigParser
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

config_filename = "data/config.cfg"

users = [("Matt","14:1a:a3:95:a7:9e"),
         ("Kat", "58:a2:b5:e9:2b:fc"),
         ("Adam","24:e3:14:d2:f8:b2")]

######################################################################
# Functions
######################################################################

def write_template_config():
    c = ConfigParser.ConfigParser()
    
    sec = "general"
    c.add_section(sec)
    c.set(sec,"data_directory","data")
    c.set(sec, "html_filename", "%(data_directory)s/index.html")
    
    sec = "temperature_thread"
    c.add_section(sec)
    c.set(sec,"data_directory","data")
    c.set(sec, "data_file", "%(data_directory)s/floor_temps.csv")
    c.set(sec, "device_names", "spark_device_1,spark_device_2,spark_device_3")
    
    sec = "furnace_control"
    c.add_section(sec)
    c.set(sec,"data_directory","data")
    c.set(sec, "set_point_filename", "%(data_directory)s/set_points.cfg")
    
    sec = "memory_thread"
    c.add_section(sec)
    c.set(sec,"data_directory","data")
    c.set(sec, "data_file", "%(data_directory)s/mem_usage.csv")
    
    sec = "user_thread"
    c.add_section(sec)
    c.set(sec, "users", "user_1,user_2,user_3")
    
    for user in ["user_1", "user_2", "user_3"]:
        c.add_section(user)
        c.set(user, "mac", "xx:xx:xx:xx:xx:xx:xx")

    c.write(open("temp.cfg","wb"))


def build_html_file(filename, thermostat, user_thread, furnace_control):
    global template_contents
    
    if DEBUG:
        print "building file"
    
    if template_contents == None:
        f = open("thermostat_template.html", "r")
        template_contents = f.read()
        f.close()
    
    content = template_contents % (user_thread.get_history(), \
                                   furnace_control.get_history(), \
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
        print "check_permissions() got error:", sys.exc_info(), " on file:", filename
        sys.exit(1)

def print_usage():
    print "Usage: python %s [config file]   default=%s" % (sys.argv[0], config_filename)
    os._exit(0)

def parse_config(filename):
    config = ConfigParser.ConfigParser()
    config.read(config_filename)
    return config


################################################################################
#
#  MAIN
#
################################################################################

if len(sys.argv) == 1:
    if not os.path.exists(config_filename):
        write_template_config()

if len(sys.argv) == 2:
    if "-h" == sys.argv[1] or "--help" == sys.argv[1]:
        print_usage()
    elif "-e" == sys.argv[1] or "--example-config" == sys.argv[1]:
        write_template_config()
        os._exit(0)
    else:
        config_filename = sys.argv[1]

config = parse_config(config_filename)

html_filename = config.get("general","html_filename")

check_permissions(html_filename)

data_dir = config.get("general","data_directory")
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

############################################################################
# Thermostat Thread
############################################################################

thermostat = temperature_thread.Temperature_Thread(config = config)

if not thermostat.isInitialized():
    print "Error creating temperature thread"
    sys.exit(1)

thermostat.start()

############################################################################
# User Thread
############################################################################
user = user_thread.User_Thread(config = config)

if not user.isInitialized():
    print "Error creating user thread"
    thermostat.stop()
    sys.exit(1)

user.start()

############################################################################
# Memory Thread
############################################################################
mem = memory_thread.Memory_Thread(config = config)

if not mem.isInitialized():
    print "Error creating memory thread"
    thermostat.stop()
    user.stop()
    sys.exit(1)

mem.start()

############################################################################
# Furnace Control Thread
############################################################################

devices = config.get("temperature_thread", "device_names").split(",")

def top_temp():
    return thermostat.get_current_device_temp(devices[0])
def main_temp():
    return thermostat.get_current_device_temp(devices[1])
def basement_temp():
    return thermostat.get_current_device_temp(devices[2])

zones = [ {'name':devices[0], 'pin':18, 'get_temp':top_temp},
          {'name':devices[1], 'pin':23, 'get_temp':main_temp},
          {'name':devices[2], 'pin':24, 'get_temp':basement_temp} ]

furnace_ctrl = furnace_control.Furnace_Control(zones, "data/set_points.cfg", "data/furnace_state.csv")

if not furnace_ctrl.isInitialized():
    print "Error creating furnace controller"
    thermostat.stop()
    user.stop()
    mem.stop()
    sys.exit(1)

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
# Cleanup
############################################################################

def receive_signal(signum, stack):
    print "Caught signal:", str(signum)
    thermostat.stop()
    user.stop()
    mem.stop()
    furnace_ctrl.stop()
    comms.stop()
    os._exit(0)

signal.signal(signal.SIGINT, receive_signal)

############################################################################
# Main loop
############################################################################

while True:
    build_html_file(html_filename, thermostat, user, furnace_ctrl)
    #os.system("/home/mlamonta/bin/blink1-tool -q --hsb=130,200,50")
    time.sleep(60)
    #os.system("/home/mlamonta/bin/blink1-tool -q --off")
        






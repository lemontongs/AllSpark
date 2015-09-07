#! /usr/bin/python

import ConfigParser
import os
import sys
import signal
import time

from plugins import object_group

DEBUG = False

template_contents = None

config_filename = "data/config.cfg"

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
    c.set(sec, "spark_auth_file", "%(data_directory)s/spark_auth.txt")
    
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


def build_html_file(filename, og):
    global template_contents
    
    if DEBUG:
        print "building file"
    
    if template_contents == None:
        f = open("thermostat_template.html", "r")
        template_contents = f.read()
        f.close()
    
    content = template_contents % (og.thermostat.get_javascript(), \
                                   og.mem.get_javascript(), \
                                   og.user_thread.get_javascript(), \
                                   og.security.get_javascript(), \
                                   og.furnace_ctrl.get_javascript(), \
                                   og.set_point.get_javascript(), \
                                   
                                   og.thermostat.get_html(), \
                                   og.furnace_ctrl.get_html(), \
                                   og.set_point.get_html(), \
                                   og.user_thread.get_html(), \
                                   og.security.get_html(), \
                                   og.mem.get_html())
    
    if DEBUG:
        print "writing file"
    
    remove_file(filename)
    f = open(filename, "w+")
    f.write(content)
    f.close()
    
def remove_file(filename):
    try:
        os.remove(filename)
    except OSError:    # its OK if the file does not exist
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
# Instantiate and initialize threads
############################################################################
og = object_group.Object_Group(config)

if not og.initialized:
    print "Error creating threads"
    sys.exit(1)

og.start()

############################################################################
# Cleanup
############################################################################
def receive_signal(signum, stack):
    print "Caught signal:", str(signum), "closing threads..."
    og.stop()
    os._exit(0)

signal.signal(signal.SIGINT, receive_signal)

############################################################################
# Main loop
############################################################################

while True:
    build_html_file(html_filename, og)
    #os.system("/home/mlamonta/bin/blink1-tool -q --hsb=130,200,50")
    time.sleep(60)
    #os.system("/home/mlamonta/bin/blink1-tool -q --off")
        






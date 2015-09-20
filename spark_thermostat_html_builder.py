#! /usr/bin/python

import ConfigParser
import os
import sys
import signal
import time
import threading

from utilities import object_group


DEBUG = False

template_contents = None

config_filename = "data/config.cfg"

######################################################################
# Functions
######################################################################

def write_template_config():
    c = ConfigParser.ConfigParser()
    
    #todo: missing general twilio and udp sections 
    
    object_group.Object_Group.get_template_config( c )
    c.write(open("example.cfg","wb"))
    print "Created ./example.cfg"


def build_html_file(filename, og):
    global template_contents
    
    if DEBUG:
        print "building file"
    
    if template_contents == None:
        f = open("thermostat_template.html", "r")
        template_contents = f.read()
        f.close()
    
    content = template_contents % ( og.get_javascript(), og.get_html() )
    
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
# Instantiate and initialize the plugins
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
    
    for t in threading.enumerate():
        print t
        






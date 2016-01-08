#! /usr/bin/python

import ConfigParser
import datetime
import logging
import logging.handlers
import os
import sys
import signal
import time

from utilities import object_group
from utilities import config_utils
from utilities import graphite_logging

template_contents = None
config_filename = "data/config.cfg"
GENERAL_CONFIG_SEC = "general"

######################################################################
# Functions
######################################################################


def write_template_config():
    c = ConfigParser.ConfigParser()
    
    # todo: missing general Twilio and udp sections
    
    object_group.ObjectGroup.get_template_config( c )
    c.write(open("example.cfg", "wb"))
    print "Created example.cfg"


def build_html_file(filename, obj_group):
    global template_contents
    
    start = datetime.datetime.now()
    
    logging.getLogger("allspark").debug("building HTML file")
    
    if template_contents is None:
        logging.getLogger("allspark").debug("reading template")
        f = open("thermostat_template.html", "r")
        template_contents = f.read()
        f.close()
        logging.getLogger("allspark").debug("done reading template")
    
    logging.getLogger("allspark").debug("filling template")
    content = template_contents % ( obj_group.get_javascript(), obj_group.get_html() )
    logging.getLogger("allspark").debug("done filling template")
    
    logging.getLogger("allspark").debug("writing HTML file")
    remove_file(filename)
    f = open(filename, "w+")
    f.write(content)
    f.close()
    logging.getLogger("allspark").debug("done writing HTML file")
    
    end = datetime.datetime.now()
    graphite_logging.send_data("allspark.htmlBuildTime", (end - start).total_seconds() )


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
    except (OSError, IOError):
        print "check_permissions() got error:", sys.exc_info(), " on file:", filename
        sys.exit(1)


def print_usage():
    print "Usage: python %s [config file]   default=%s" % (sys.argv[0], config_filename)
    sys.exit()


def parse_config(filename):
    c = ConfigParser.ConfigParser()
    c.read(filename)
    return c


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
        sys.exit()
    else:
        config_filename = sys.argv[1]

config = parse_config(config_filename)

log_filename = config_utils.get_config_param(config, GENERAL_CONFIG_SEC, "log_filename")
if log_filename is None:
    print "log_filename property missing from " + GENERAL_CONFIG_SEC + " section"
    sys.exit(1)
    
log_level = config_utils.get_config_param(config, GENERAL_CONFIG_SEC, "log_level")
if log_level is None:
    print "log_level property missing from " + GENERAL_CONFIG_SEC + " section"
    sys.exit(1)

html_filename = config_utils.get_config_param(config, GENERAL_CONFIG_SEC, "html_filename")
if html_filename is None:
    print "html_filename property missing from " + GENERAL_CONFIG_SEC + " section"
    sys.exit(1)

data_directory = config_utils.get_config_param(config, GENERAL_CONFIG_SEC, "data_directory")
if data_directory is None:
    print "data_directory property missing from " + GENERAL_CONFIG_SEC + " section"
    sys.exit(1)

if not os.path.exists(data_directory):
    os.makedirs(data_directory)

check_permissions(html_filename)

if type(logging.getLevelName(log_level)) is str:
    print "WARNING: Invalid log level detected '" + log_level + "'. Using DEBUG log level."
    log_level = "DEBUG"

############################################################################
# Set up the logger
############################################################################
format_str = '%(asctime)s %(name)-30s %(levelname)-8s %(message)s'
logging.getLogger('').handlers = []

logging.basicConfig(level=logging.getLevelName(log_level),
                    format=format_str,
                    datefmt='%Y-%m-%d %H:%M:%S')

# define a Handler which writes messages to a file
file_handler = logging.handlers.TimedRotatingFileHandler(filename=log_filename, 
                                                         when="midnight", 
                                                         backupCount = 10)  # only keep 10 days of logs
file_handler.setLevel(logging.getLevelName(log_level))
file_handler.setFormatter(logging.Formatter(format_str))

# add the handler to the logger
logging.getLogger('allspark').addHandler(file_handler)
logging.getLogger("requests").setLevel(logging.WARNING)

logging.getLogger('allspark').info("System Started!")

############################################################################
# Instantiate and initialize the plugins
############################################################################
og = object_group.ObjectGroup(config)

if not og.is_initialized():
    logging.error("Error creating threads")
    sys.exit(1)

og.start()

############################################################################
# Cleanup
############################################################################


def receive_signal(signum, _):
    logging.getLogger('allspark').info( "Caught signal: " + str(signum) + " closing threads..." )
    og.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, receive_signal)

############################################################################
# Main loop
############################################################################

while True:
    build_html_file(html_filename, og)
    # os.system("/home/mlamonta/bin/blink1-tool -q --hsb=130,200,50")
    time.sleep(60)
    # os.system("/home/mlamonta/bin/blink1-tool -q --off")
    
       






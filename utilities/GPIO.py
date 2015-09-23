
import logging

logger = logging.getLogger('allspark.gpio')

BCM = "BCM"
OUT = "OUT"

def setmode(mode):
    logger.debug("setmode: "+str(mode))

def setup(pin, direction):
    logger.debug("setup: "+str(pin)+" direction: "+direction)

def cleanup():
    logger.debug("cleanup")

def output(pin, state):
    logger.debug("output: pin: "+str(pin)+" state: "+str(state))


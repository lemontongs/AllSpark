
BCM = "BCM"
OUT = "OUT"

def setmode(mode):
    print "GPIO: setmode: "+str(mode)

def setup(pin, direction):
    print "GPIO: setup: "+str(pin)+" direction: "+direction

def cleanup():
    print "GPIO: cleanup"

def output(pin, state):
    print "GPIO: output: pin: "+str(pin)+" state: "+str(state)


#!/usr/bin/env python

import sys
import cgi
import zmq

import cgitb

cgitb.enable()


def send_message(msg):
    try:
        context = zmq.Context()
        socket = context.socket(zmq.PAIR)
        socket.setsockopt(zmq.LINGER, 2000)
        socket.connect("tcp://localhost:5555")
        socket.send(msg)
    except zmq.ZMQBaseError:
        print sys.exc_info()


def send_temperature(sp, f):
    send_message("set_point,%s,%s" % (f, str(sp)))


def disarm_alarm():
    send_message("alarm,disarm")


def arm_alarm():
    send_message("alarm,arm")


def send_zwave_command(dev, val):
    send_message("zwave,%s,%s" % (dev, val))

###############################################################################
# MAIN
###############################################################################

# print header
print "Content-type: text/html\n\n"
form = cgi.FieldStorage()

#
# Furnace set point control
#
if ('set_temp' in form) and ('floor' in form):
    try:
        set_point = float(form['set_temp'].value)
        floor = form['floor'].value

        if set_point > 80:
            print "set point too high"
        elif set_point < 50:
            print "set point too low"
        elif (floor != "top_floor_temp") and (floor != "basement_floor_temp") and (floor != "main_floor_temp"):
            print "invalid floor:", floor
        else:
            print "OK"
            send_temperature(set_point, floor)
    except ValueError:
        print "bad temp", sys.exc_info()

#
# Security arm/disarm control
#
elif 'set_alarm' in form:
    command = form['set_alarm'].value

    if command == "arm":
        print "ARMED"
        arm_alarm()
    elif command == "disarm":
        print "DISARMED"
        disarm_alarm()
    else:
        print "INVALID"

#
# ZWave device control
#
elif 'set_zwave' in form:
    try:
        value  = int(form['set_zwave'].value) # dimmer value 0-255 or 0/1 for switch
        device = form['device'].value    # uid of dimmer/switch

        if value < 0 or value > 255:
            print "Invalid value:", value
        else:
            print "OK"
            send_zwave_command(device, value)

    except ValueError:
        print "Invalid value:", form['set_zwave'].value


else:
    print "INVALID REQUEST"

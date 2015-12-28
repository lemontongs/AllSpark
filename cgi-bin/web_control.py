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
    except:
        print sys.exc_info()


def send_temperature(sp, f):
    send_message("set_point,%s,%s" % (f, str(sp)))


def disarm_alarm():
    send_message("alarm,disarm")


def arm_alarm():
    send_message("alarm,arm")


# print header
print "Content-type: text/html\n\n"

form = cgi.FieldStorage()

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
    except:
        print "bad temp", sys.exc_info()

elif 'set_alarm' in form:
    try:
        command = form['set_alarm'].value

        if command == "arm":
            print "ARMED"
            arm_alarm()
        elif command == "disarm":
            print "DISARMED"
            disarm_alarm()
        else:
            print "INVALID"
    except:
        print "INVALID", sys.exc_info()

else:
    print "INVALID"

#!/usr/bin/env python

import socket
import time

CARBON_SERVER = 'home-server'
CARBON_PORT   = 2003


def send_data(name, value):
    message = '%s %s %d\n' % ( str(name), str(value), int(time.time()) )

    try:
        sock = socket.socket()
        sock.connect((CARBON_SERVER, CARBON_PORT))
        sock.sendall(message)
        sock.close()
    except:
        pass
    finally:
        sock.close()

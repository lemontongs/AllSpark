#!/usr/bin/env python

import socket
import time

CARBON_SERVER = 'home-server'
CARBON_PORT   = 2003


def send_data(name, value):
    message = '%s %s %d\n' % ( str(name), str(value), int(time.time()) )

    sock = socket.socket()

    try:
        sock.connect((CARBON_SERVER, CARBON_PORT))
        sock.sendall(message)
        sock.close()
    except socket.error:
        pass
    finally:
        sock.close()

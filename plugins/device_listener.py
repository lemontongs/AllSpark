#!/usr/bin/env python

import logging
from threading import Lock
from utilities.thread_base import AS_Thread
from utilities.udp_interface import UDP_Socket


CONFIG_SEC_NAME = "device_listener"

logger = logging.getLogger('allspark.' + CONFIG_SEC_NAME)

LISTEN_ADDR = "225.1.1.1"
LISTEN_PORT = 5100

class Device_Listener(AS_Thread):
    
    def __init__(self):
        AS_Thread.__init__(self, CONFIG_SEC_NAME)
        
        self._udp = UDP_Socket(LISTEN_ADDR, LISTEN_PORT)
        self._udp.start()
        
        self._devices = {}
        self._devices_lock = Lock()
        
        self._initialized = True
        
    
    def private_run(self):
        msg = self._udp.get(timeout = 2)
        if msg:
            (_,data) = msg
            
            segments = data.split(":")
            
            if len(segments) == 3:
                device_id         = segments[0]
                device_ip         = segments[1]
                device_capability = segments[2]
                
                self._devices_lock.acquire()
                
                if device_id not in self._devices:
                    logger.info("Found a new device: " + device_id + \
                                " with capability: " + device_capability + \
                                " at: " + device_ip)
                else:
                    dev = self._devices[ device_id ]
                    
                    # Device IP address change
                    if dev['address'] != device_ip:
                        logger.info("Device: " + device_id + \
                                    " address changed from: " + dev['address'] + \
                                    " to: " + device_ip)
                         
                    if  dev['capability'] != device_capability:
                        logger.info("Device: " + device_id + \
                                    " capability changed from: " + dev['capability'] + \
                                    " to: " + device_capability)
                    
                self._devices[ device_id ] = {'address':device_ip, 'capability':device_capability}
                
                self._devices_lock.release()
        
    def private_run_cleanup(self):
        self._udp.stop()
        
    def get_devices(self):
        if self.isInitialized():
            return self._devices
        

if __name__ == '__main__':
    import time
    
    logging.getLogger('').handlers = []
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    format_str = '%(asctime)s %(name)-30s %(levelname)-8s %(message)s'
    console.setFormatter(logging.Formatter(format_str))
    logger.addHandler(console)
    
    print "Unit test started!"
    
    l = Device_Listener()
    l.start()
    
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print "Unit test interrupted!"
        pass
    
    l.stop()
    
    
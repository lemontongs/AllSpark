#!/usr/bin/env python

import logging
from threading import Lock
from utilities.thread_base import ThreadedPlugin
from utilities.udp_interface import UDPSocket


PLUGIN_NAME = "device_listener"
LISTEN_ADDR = "225.1.1.1"
LISTEN_PORT = 5100


class DeviceListenerPlugin(ThreadedPlugin):

    @staticmethod
    def get_dependencies():
        return []

    def __init__(self, object_group, config):
        ThreadedPlugin.__init__(self, config=config, object_group=object_group, plugin_name=PLUGIN_NAME)

        if not self.enabled:
            return

        self._udp = UDPSocket(LISTEN_ADDR, LISTEN_PORT, LISTEN_PORT, PLUGIN_NAME + "_inf")
        self._udp.start()
        
        self._devices = {}
        self._devices_lock = Lock()
        
        self._initialized = True

    def private_run(self):
        msg = self._udp.get(timeout = 2)
        if msg:
            (_, data) = msg
            
            segments = data.split(":")
            
            if len(segments) == 3:
                device_id         = segments[0]
                device_ip         = segments[1]
                device_capability = segments[2]
                
                self._devices_lock.acquire()
                
                if device_id not in self._devices:
                    self.logger.info("Found a new device: " + device_id +
                                     " with capability: " + device_capability +
                                     " at: " + device_ip)
                else:
                    dev = self._devices[ device_id ]
                    
                    # Device IP address change
                    if dev['address'] != device_ip:
                        self.logger.info("Device: " + device_id +
                                         " address changed from: " + dev['address'] +
                                         " to: " + device_ip)
                         
                    if dev['capability'] != device_capability:
                        self.logger.info("Device: " + device_id +
                                         " capability changed from: " + dev['capability'] +
                                         " to: " + device_capability)
                    
                self._devices[ device_id ] = {'address': device_ip, 'capability': device_capability}
                
                self._devices_lock.release()
        
    def private_run_cleanup(self):
        self._udp.stop()
        
    def get_devices(self):
        if self.is_initialized():
            return self._devices
        

if __name__ == '__main__':
    import time

    logging.getLogger('').handlers = []
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    format_str = '%(asctime)s %(name)-30s %(levelname)-8s %(message)s'
    console.setFormatter(logging.Formatter(format_str))
    logging.getLogger("AllSpark." + PLUGIN_NAME).addHandler(console)

    print "Unit test started!"
    
    l = DeviceListenerPlugin()
    l.start()
    
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print "Unit test interrupted!"
        pass
    
    l.stop()

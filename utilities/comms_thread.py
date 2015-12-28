#! /usr/bin/env python

import sys
import time
from threading import Thread, Lock
import os
import zmq
import logging

logger = logging.getLogger('allspark.comms_thread')


class Comms_Thread(Thread):
    def __init__(self, port):
        Thread.__init__(self, name="comms_thread")
        self._initialized = False
        self._run_lock = Lock()
        self.port = port
        
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.PAIR)
            self.socket.bind("tcp://*:" + str(self.port))
        except:
            logger.error( "Failed to start comms thread: " + repr(sys.exc_info()) )
            return
        
        self.callbacks = {}
        self._running = False
        self._initialized = True

    def isInitialized(self):
        return self._initialized

    def stop(self):
        if self._initialized and self._running:
            
            # Send a quit message to close the thread
            context = zmq.Context()
            sock = context.socket(zmq.PAIR)
            sock.connect("tcp://localhost:" + str(self.port))
            sock.send("quit")
             
            self._initialized = False
            self._running = False
            self._run_lock.acquire()

    def register_callback(self, topic, func):
        if topic not in self.callbacks:
            self.callbacks[topic] = [func]
        else:
            self.callbacks[topic].append(func)

    def run(self):
        
        logger.info( "Thread started" )
        
        if not self._initialized:
            logger.error( "Started before _initialized, not _running" )
            return
        
        f = open("logs/comms_log","a")

        self._running = self._run_lock.acquire()
        while self._running:
            
            msg = self.socket.recv()
            
            logger.info( "Thread executed" )
        
            f.write(str(time.time())+" GOT: "+str(msg)+"\n")
            f.flush()
            
            if msg == "quit":
                break
            
            # message format:  topic,something,something ...
            topic = msg.split(',')[0]
            if topic not in self.callbacks:
                f.write('nobody is registered for topic: "' + topic + '"\n')
                f.flush()
                continue
             
            # call each registered callback
            functions = self.callbacks[topic]
            for func in functions:
                f.write("calling: "+func.__name__+"\n")
                f.flush()
                func(msg)
             
        f.close()
        
        logger.info( "Thread stopped" )
        
        self._run_lock.release()

#
# MAIN
#
if __name__ == "__main__":
    
    def send_test():
        context = zmq.Context()
        sock = context.socket(zmq.PAIR)
        sock.connect("tcp://localhost:5555")
        sock.send("test,1,2,3,4")
    
    def test_callback(msg):
        print msg
    
    comms = Comms_Thread()
    
    if not comms.isInitialized():
        print "Failed to initialize"
        os._exit(0)
    
    comms.register_callback("test", test_callback)
    comms.start()
    
    print "Listening for messages for 10 seconds..."
    time.sleep(5)
    send_test()
    time.sleep(5)
    
    comms.stop()

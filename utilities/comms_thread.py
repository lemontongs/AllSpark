#! /usr/bin/env python

import sys
import time
from threading import Thread, Lock
import os
import zmq

class Comms_Thread(Thread):
    def __init__(self, port):
        Thread.__init__(self)
        self.initialized = False
        self.run_lock = Lock()
        self.port = port
        
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.PAIR)
            self.socket.bind("tcp://*:" + str(self.port))
        except:
            print "Failed to start comms thread:", sys.exc_info()
            return
        
        self.callbacks = {}
        self.running = False
        self.initialized = True

    def isInitialized(self):
        return self.initialized

    def stop(self):
        if self.initialized and self.running:
            
            # Send a quit message to close the thread
            context = zmq.Context()
            sock = context.socket(zmq.PAIR)
            sock.connect("tcp://localhost:" + str(self.port))
            sock.send("quit")
             
            self.initialized = False
            self.running = False
            self.run_lock.acquire()

    def register_callback(self, topic, func):
        if topic not in self.callbacks:
            self.callbacks[topic] = [func]
        else:
            self.callbacks[topic].append(func)

    def run(self):
        
        if not self.initialized:
            print "Warning: started before initialized, not running"
            return
        
        f = open("logs/comms_log","a")

        self.running = self.run_lock.acquire()
        while self.running:
            
            msg = self.socket.recv()
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
        self.run_lock.release()

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

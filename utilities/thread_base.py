#!/usr/bin/env python

import sys
import traceback
import logging
from threading import Thread, Lock

class AS_Thread(Thread):
    
    def __init__(self, config_sec_name):
        Thread.__init__(self, name=config_sec_name)
        self._run_lock    = Lock()
        self._initialized = False
        self._running     = False
        self.logger       = logging.getLogger('allspark.' + config_sec_name)
        
    def isInitialized(self):
        return self._initialized
          
    def isRunning(self):
        return self._running
            
    def stop(self):
        if self.isInitialized() and self.isRunning():
            self._running = False    # Signal thread to stop
            self._run_lock.acquire() # Wait for thread to stop
    
    def private_run(self):
        self.logger.warning("private_run function not overridden!")
        self._running = False
    
    def private_run_cleanup(self):
        pass
    
    def run(self):
        
        self.logger.info( "Thread started" )
        
        if not self.isInitialized():
            self.logger.error( "Start called before _initialized, not _running" )
            return
        
        #############
        # MAIN LOOP #
        #############
        self._running = self._run_lock.acquire()
        while self._running:
            
            try:
                self.private_run()
            except Exception as e:
                tb = "".join( traceback.format_tb(sys.exc_info()[2]) )
                self.logger.error( "exception occured in " + self.name + " thread: \n" + tb + "\n" + str( e ) ) 
        
        self.private_run_cleanup()
        
        self.logger.info( "Thread stopped" )
        self._run_lock.release()
        
#!/usr/bin/env python

import sys
import traceback
import time
import logging
from threading import Thread, Lock


class ASThread(Thread):
    
    def __init__(self, config_sec_name):
        Thread.__init__(self, name=config_sec_name)
        self._run_lock    = Lock()
        self._initialized = False
        self._running     = False
        self.logger       = logging.getLogger('allspark.' + config_sec_name)
        self.daemon       = True  # thread dies with program
        
    def is_initialized(self):
        return self._initialized
          
    def is_running(self):
        return self._running
            
    def stop(self):
        if self.is_initialized() and self.is_running():
            self.logger.info( "Stopping thread" )
            self._running = False     # Signal thread to stop
            self._run_lock.acquire()  # Wait for thread to stop
    
    def private_run(self):
        self.logger.warning("private_run function not overridden!")
        self._running = False
    
    def private_run_cleanup(self):
        pass
    
    def run(self):
        
        self.logger.info( "Thread started" )
        
        if not self.is_initialized():
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
                time.sleep(5)
        
        self.private_run_cleanup()
        
        self.logger.info( "Thread stopped" )
        self._run_lock.release()

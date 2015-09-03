
import os
import time
from threading import Thread, Lock

OPEN   = '0'
CLOSED = '1'

class Security_Thread(Thread):
    def __init__(self, object_group, config):
        Thread.__init__(self)
        self.og = object_group
        self.initialized = False
        self.mutex = Lock()
        self.running = False
        config_sec = "security_thread"

        if config_sec not in config.sections():
            print config_sec + " section missing from config file"
            return

        if "monitor_device_name" not in config.options(config_sec):
            print "monitor_device_name property missing from " + config_sec + " section"
            return

        self.monitor_device_name = config.get(config_sec, "monitor_device_name")

        if "num_zones" not in config.options(config_sec):
            print "num_zones property missing from " + config_sec + " section"
            return

        self.num_zones = int(config.get(config_sec, "num_zones"))
        self.zones = []
        
        for zone in range(self.num_zones):
            zone_index = "zone_"+str(zone)
            
            if zone_index not in config.options(config_sec):
                print zone_index+" property missing from " + config_sec + " section"
                return
                
            self.zones.append( {'last':time.localtime(), 'state':CLOSED, 'name':config.get(config_sec, zone_index)} )

        #print self.zones

        if "collect_period" not in config.options(config_sec):
            self.collect_period = 5
        else:
            self.collect_period = float(config.get(config_sec, "collect_period", True))
        
        self.sensor_states = ""
        self.initialized = True
    
    def isInitialized(self):
        return self.initialized
    
    def getSensorStates(self):
        self.mutex.acquire()
        ss = self.sensor_states
        self.mutex.release()
        return ss
    
    def run(self):
        
        if not self.initialized:
            print "Warning: Security_Thread started before initialized, not running."
            return
        
        self.running = True
        while self.running:
          
            self.mutex.acquire()
            self.sensor_states = ""
            state_str = self.og.spark.getVariable( self.monitor_device_name, "state")
            
            for zone in range(self.num_zones):
                
                state = state_str[zone]
                
                # record state changes
                if state != self.zones[zone]['state']:
                    self.zones[zone]['state'] = state
                    self.zones[zone]['last']  = time.localtime()
    
                # <tr class="success">
                #     <td>Zone 1</td>
                #     <td>Open</td>
                #     <td>Yesterday</td>
                # </tr>
                
                entry = '\n<tr class="'
                if state == CLOSED:
                    entry += 'success">\n'
                else:
                    entry += 'danger">\n'
                
                entry += '    <td>'+self.zones[zone]['name']+'</td>\n'
                
                if state == CLOSED:
                    entry += "    <td>closed</td>\n"
                else:
                    entry += "    <td>open</td>\n"
                
                entry += '    <td>'+ time.strftime('%b %d %I:%M%p', self.zones[zone]['last']) +'</td>\n'
                entry += '</tr>\n'
                
                self.sensor_states += entry
              
            self.mutex.release()
          
            time.sleep(self.collect_period)
  
    def stop(self):
        self.running = False
    
            
            
if __name__ == "__main__":
    
    sec = Security_Thread()
    
    if not sec.isInitialized():
        print "ERROR: initialization failed"
        os._exit(0)
    
    sec.start()
    
    print "Collecting data (1 minute)..."
    time.sleep(60)
    
    #print sec.get_history()
    
    sec.stop()

            
            
            
            
            
            
            
            
            
            
            
            

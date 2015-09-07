
from threading import Thread
import socket
import select
import Queue

# addr = "225.1.1.1"
# port = 5100
# interface = "0.0.0.0"

class UDP_Interface(Thread):
    def __init__(self, config):
        Thread.__init__(self)
        self.initialized = False

        config_sec = "udp"
        
        if config_sec not in config.sections():
            print config_sec + " section missing from config file"
            return
        
        if "multicast_address" not in config.options(config_sec):
            print "multicast_address property missing from " + config_sec + " section"
            return
        self.multicast_address = config.get(config_sec, "multicast_address")
        
        
        if "port" not in config.options(config_sec):
            print "port property missing from " + config_sec + " section"
            return
        port = int(config.get(config_sec, "port"))
               

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 20)
        self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)
        
        self.sock.bind(('', port))
        
        self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton("0.0.0.0"))
        self.sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self.multicast_address) + socket.inet_aton("0.0.0.0"))
        
        self.sock.setblocking(0)
        
        self.messages = Queue.Queue()
        
        self.initialized = True
        
    def isInitialized(self):
        return self.initialized
            
    def stop(self):
        self.running = False
    
    def get(self, timeout=0):
        if self.initialized:
            
            try:
                if timeout > 0:
                    msg = self.messages.get(True, timeout)
                else:
                    msg = self.messages.get_nowait()
                    
                return msg
            except Queue.Empty:
                pass
        return None
    
    def run(self):
        
        if not self.initialized:
            print "Warning: start called before initialized, not running"
            return
        
        #############
        # MAIN LOOP #
        #############
        self.running = True
        while self.running:
            
            # Wait for data
            ready = select.select([self.sock], [], [], 1) # 1 second timeout
            if ready[0]:
                data, sender_addr = self.sock.recvfrom(4096)
                self.messages.put( (sender_addr, data) )
                
        
        # Unregister multicast receive membership, then close the port
        self.sock.setsockopt(socket.SOL_IP, socket.IP_DROP_MEMBERSHIP, socket.inet_aton(self.multicast_address) + socket.inet_aton('0.0.0.0'))
        self.sock.close()
        

if __name__ == "__main__":
    import ConfigParser, time
    
    config = ConfigParser.ConfigParser()
    config.read("data/config.cfg")
    
    udp = UDP_Interface(config)

    udp.start()
    
    time.sleep(5)
    
    udp.stop()




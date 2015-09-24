
from threading import Thread, Lock
from utilities import config_utils
import logging
import socket
import select
import Queue

# addr = "225.1.1.1"
# port = 5100
# interface = "0.0.0.0"

CONFIG_SEC_NAME = "udp"

logger = logging.getLogger('allspark.'+CONFIG_SEC_NAME)

class UDP_Interface(Thread):
    def __init__(self, config):
        Thread.__init__(self, name=CONFIG_SEC_NAME)
        self.initialized = False
        self.run_lock = Lock()
        
        if not config_utils.check_config_section( config, CONFIG_SEC_NAME ):
            return

        self.multicast_address = config_utils.get_config_param( config, CONFIG_SEC_NAME, "multicast_address")
        if self.multicast_address == None:
            return
        
        port = config_utils.get_config_param( config, CONFIG_SEC_NAME, "port")
        if port == None:
            return
        port = int(port)
        
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
        self.run_lock.acquire() # Wait for the thread to stop
    
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
        
        logger.info( "Thread started" )
        
        if not self.initialized:
            logger.error( "Start called before initialized, not running" )
            return
        
        #############
        # MAIN LOOP #
        #############
        self.running = self.run_lock.acquire()
        while self.running:
            
            # Wait for data
            logger.info( "Waiting for message" )
            ready = select.select([self.sock], [], [], 1) # 1 second timeout
        
            if ready[0]:
                data, sender_addr = self.sock.recvfrom(4096)
                self.messages.put( (sender_addr, data) )
                logger.info( "Got message: " + data )
                
        # Unregister multicast receive membership, then close the port
        self.sock.setsockopt(socket.SOL_IP, socket.IP_DROP_MEMBERSHIP, socket.inet_aton(self.multicast_address) + socket.inet_aton('0.0.0.0'))
        self.sock.close()
        
        logger.info( "Thread stopped" )
        self.run_lock.release()
        

if __name__ == "__main__":
    import ConfigParser, time
    
    config = ConfigParser.ConfigParser()
    config.read("data/config.cfg")
    
    udp = UDP_Interface(config)

    udp.start()
    
    time.sleep(5)
    
    udp.stop()




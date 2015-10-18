
from thread_base import AS_Thread
import logging
import socket
import select
import Queue

# addr = "225.1.1.1"
# port = 5100
# interface = "0.0.0.0"

CONFIG_SEC_NAME = "udp"

logger = logging.getLogger('allspark.'+CONFIG_SEC_NAME)

class UDP_Socket(AS_Thread):
    def __init__(self, address, port, thread_name = "udp_socket"):
        AS_Thread.__init__(self, thread_name)
        
        self.address = address
        if self.address == None:
            return
        
        if port == None:
            return
        try:
            self.port = int(port)
        except ValueError:
            return
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 20)
        self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)
        
        self.sock.bind(('', self.port))
        
        self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton("0.0.0.0"))
        self.sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self.address) + socket.inet_aton("0.0.0.0"))
        
        self.sock.setblocking(0)
        
        self.messages = Queue.Queue()
        
        self._initialized = True
        
    def get(self, timeout=0):
        if self.isInitialized():
            try:
                if timeout > 0:
                    msg = self.messages.get(True, timeout)
                else:
                    msg = self.messages.get_nowait()
                    
                return msg
            except Queue.Empty:
                pass
        return None
    
    def send_message(self, message):
        self.sock.sendto(message.encode('utf-8'), (self.address, self.port))
    
    def private_run(self):
        # Wait for data
        ready = select.select([self.sock], [], [], 1) # 1 second timeout
    
        if ready[0]:
            data, sender_addr = self.sock.recvfrom(4096)
            self.messages.put( (sender_addr, data) )
            logger.info( "Got message: " + data )
    
    def private_run_cleanup(self):
        # Unregister multicast receive membership, then close the port
        self.sock.setsockopt(socket.SOL_IP, socket.IP_DROP_MEMBERSHIP, socket.inet_aton(self.address) + socket.inet_aton('0.0.0.0'))
        self.sock.close()
        

if __name__ == "__main__":
    import time
    
    udp = UDP_Socket("225.1.1.1", 5100)

    udp.start()
    
    for _ in range(10):
        time.sleep(1)
        print udp.get()
    
    udp.stop()




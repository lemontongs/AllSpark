
from thread_base import ASThread
import logging
import socket
import select
import Queue


class UDPSocket(ASThread):
    def __init__(self, address, rx_port, tx_port, thread_name = "udp_interface"):
        ASThread.__init__(self, thread_name)
        self.logger = logging.getLogger('allspark.' + thread_name)
        
        self.address = address
        if self.address is None:
            self.logger.error("Address is None")
            return
        
        if rx_port is None:
            self.logger.error("rx_port is None")
            return
        
        if tx_port is None:
            self.logger.error("tx_port is None")
            return
        
        try:
            self.rx_port = int(rx_port)
        except ValueError:
            self.logger.error("invalid rx_port: " + str(rx_port) )
            return
        
        try:
            self.tx_port = int(tx_port)
        except ValueError:
            self.logger.error("invalid tx_port: " + str(tx_port) )
            return
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 20)
        self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)
        
        self.sock.bind(('', self.rx_port))
        
        self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton("0.0.0.0"))
        self.sock.setsockopt(socket.SOL_IP,
                             socket.IP_ADD_MEMBERSHIP,
                             socket.inet_aton(self.address) + socket.inet_aton("0.0.0.0"))
        
        self.sock.setblocking(0)
        
        self.messages = Queue.Queue()
        
        self._initialized = True
    
    def clear(self):
        if self.is_initialized():
            try:
                while True:
                    self.messages.get_nowait()
            except Queue.Empty:
                self.logger.debug( "cleared" )
    
    def get(self, timeout=0):
        if self.is_initialized():
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
        self.logger.debug( "sending message: " + message )
        self.sock.sendto(message.encode('utf-8'), (self.address, self.tx_port))
    
    def private_run(self):
        # Wait for data
        ready = select.select([self.sock], [], [], 1)  # 1 second timeout
    
        if ready[0]:
            data, sender_addr = self.sock.recvfrom(4096)
            self.messages.put( (sender_addr, data) )
            self.logger.debug( "Got message: " + data )
    
    def private_run_cleanup(self):
        # Unregister multicast receive membership, then close the port
        self.sock.setsockopt(socket.SOL_IP,
                             socket.IP_DROP_MEMBERSHIP,
                             socket.inet_aton(self.address) + socket.inet_aton('0.0.0.0'))
        self.sock.close()
        self.logger.debug( "cleanup" )
        

if __name__ == "__main__":
    
    udp = UDPSocket("225.1.1.2", 5400, 5300)

    udp.start()
    
    udp.send_message("00")
    print udp.get(10)
    
    udp.stop()




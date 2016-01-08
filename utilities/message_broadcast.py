
import socket
from plugin import Plugin


class MessageBroadcast(Plugin):

    @staticmethod
    def get_dependencies():
        return []

    def __init__( self, address="225.1.1.1", port=5200, interface="0.0.0.0" ):
        Plugin.__init__(self, "broadcast")

        self.address   = address
        self.port      = port
        self.interface = interface

        try:
            # Instantiate a UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

            # Allow address reuse
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Set the packets TTL
            self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 1)

            # Do not loop messages back to the local sockets
            self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 0)

            # Bind to the port
            self.sock.bind(('', self.port))

            # Set the interface to perform the multicast on
            self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(self.interface))

            # Apply for messages sent to the specified address
            self.sock.setsockopt(socket.SOL_IP,
                                 socket.IP_ADD_MEMBERSHIP,
                                 socket.inet_aton(self.address) + socket.inet_aton(self.interface))

            self._initialized = True

        except socket.error:
            pass

    def send(self, msg):
        self.sock.sendto( msg, (self.address, self.port) )
        
    def __del__(self):
        if self.is_initialized():
            # Close the socket
            self.sock.close()

if __name__ == '__main__':
    m = MessageBroadcast()
    m.send("HELLO WORLD!")

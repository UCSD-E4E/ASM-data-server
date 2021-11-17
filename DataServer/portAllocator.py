import socket


class PortAllocator:
    """This class provides a method to allocate the next available port in the
    given block of ports.
    """

    def __init__(self, block_start: int, block_end: int) -> None:
        """Initializes the allocator with the specified block of ports
        Args:
            block_start (int): Starting number of block of ports, inclusive
            block_end (int): Ending number of block of ports, inclusive
        """

        self.__s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.__start = block_start
        self.__end = block_end

        self.__portDict = {}
        self.__hostname = self.__s.gethostname()

        self.__ip = self.__s.gethostbyname(self.__hostname)

        # TODO reimplement this
        
    def isOpen(self, ip, port):
        try:
            self.__s.connect((ip, port))
            self.__s.shutdown(2)
            return True 
        except:
            return False

    def createDict(self):
        for i in range(self.__start, self.__end):
            self.__portDict[i] = self.isOpen(self.__ip, i)

    def reservePort(self) -> int:
        """Retrieves the next available port in the specified block of ports.
        This method must check that the port returned is currently available.
        Once this method returns a particular port, it must not return that 
        port until PortAllocator.releasePort is called on that port.  This
        method must throw an exception if no ports are currently available.

        Raises:
            RuntimeError: No free ports

        Returns:
            int: Next available port number
        """

        for i in self.__portDict:
            if self.__portDict[i]:
                return_port = i
                self.__portDict[i] == False
            else:
                continue

        if return_port > self.__end:
            raise RuntimeError('All ports occupied')
        return return_port

    def releasePort(self, port: int) -> None:
        """Releases the lock on the specified port.  After calling this method
        on a specific port, that port may be returned by
        PortAllocator.reservePort.  Passing in an already released port or a
        port not in the specified block shall not result in any internal state
        change. 

        Args:
            port (int): Port to release
        """

        if port > self.__end or port < self.__start:
            raise RuntimeError('Invalid port')

        try:
            self.__s.bind((self.__ip, port))
            self.__s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.__portDict[port] = True
        except:
            raise RuntimeError
        

        
        
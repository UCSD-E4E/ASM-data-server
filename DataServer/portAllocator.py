from __future__ import annotations
from enum import Enum, auto
import socket
from typing import Dict

class PortAllocator:
    """This class provides a method to allocate the next available port in the
    given block of ports.
    """

    class PortStatus(Enum):
        UNKNOWN=auto()
        RESERVED=auto()
        RELEASED=auto()
        USED=auto()

    def __init__(self, block_start: int, block_end: int) -> None:
        """Initializes the allocator with the specified block of ports
        Args:
            block_start (int): Starting number of block of ports, inclusive
            block_end (int): Ending number of block of ports, inclusive
        """

        self.__start = block_start
        self.__end = block_end

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            self.__ip = sock.getsockname()[0]

        self.__portDict: Dict[int, PortAllocator.PortStatus] = {i:PortAllocator.PortStatus.UNKNOWN for i in range(block_start, block_end)}
        self.__reservedPorts: Dict[int, socket.socket] = {}

    def __isOpen(self, port:int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((self.__ip, port))
                return True
            except:
                return False

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
        free_ports = [port for port, status in self.__portDict.items() if status == PortAllocator.PortStatus.RELEASED]
        for port in free_ports:
            assert(port in self.__reservedPorts)
            self.__reservedPorts[port].close()
            self.__reservedPorts.pop(port)
            self.__portDict[port] = PortAllocator.PortStatus.RESERVED
            return port
        
        unknown_ports = [port for port, status in self.__portDict.items() if status == PortAllocator.PortStatus.UNKNOWN]
        for port in unknown_ports:
            if self.__isOpen(port):
                self.__portDict[port] = PortAllocator.PortStatus.RESERVED
                return port
            else:
                self.__portDict[port] = PortAllocator.PortStatus.USED
        
        used_ports = [port for port, status in self.__portDict.items() if status == PortAllocator.PortStatus.USED]
        for port in used_ports:
            if self.__isOpen(port):
                self.__portDict[port] = PortAllocator.PortStatus.RESERVED
                return port
        
        raise RuntimeError("No free ports")
        

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
        if port in self.__reservedPorts:
            raise RuntimeError("Double free on port!")
        self.__reservedPorts[port] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__reservedPorts[port].bind((self.__ip, port))
        self.__reservedPorts[port].listen(1)
        self.__portDict[port] = PortAllocator.PortStatus.RELEASED
        

        
        
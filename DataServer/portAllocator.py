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
        self.__start = block_start
        self.__end = block_end

        # TODO reimplement this
        self.__current = self.__start

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
        
        # TODO reimplement this
        self.__current += 1
        if self.__current > self.__end:
            raise RuntimeError
        return self.__current

    def releasePort(self, port: int) -> None:
        """Releases the lock on the specified port.  After calling this method
        on a specific port, that port may be returned by
        PortAllocator.reservePort.  Passing in an already released port or a
        port not in the specified block shall not result in any internal state
        change.

        Args:
            port (int): Port to release
        """
        # TODO reimplement this
        pass
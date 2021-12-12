from typing import Dict
from DataServer.portAllocator import PortAllocator
import socket
import os

def test_PortAllocator():
    start_port = 10200
    end_port = 10300
    allocator = PortAllocator(start_port, end_port)
    assert(allocator is not None)
    available_ports = set()

    # Discover public interface IP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(("8.8.8.8", 80))
        HOST = sock.getsockname()[0]

    # Discover set of available ports
    for port_num in range(start_port, end_port, 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((HOST, port_num))
                result = 0
            except: # pragma: no cover
                result = 1 # pragma: no cover
            if result == 0:
                available_ports.add(port_num)
            else:
                print(f'Unable to open port {port_num}, error code {os.strerror(result)}') # pragma: no cover

    # This test is not valid if there are no available ports!
    assert(len(available_ports) != 0)
    sockets: Dict[int, socket.socket] = {}
    total_ports = len(available_ports)
    count = 0

    # Let's pretend one of these is a bad port and isn't available
    # make the bad port
    bad_port = list(available_ports)[0]
    bad_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bad_sock.bind((HOST, bad_port))
    bad_sock.listen(1)
    available_ports.remove(bad_port)


    # Try to reserve the rest of the ports.  We should be able to
    while len(available_ports) > 0:
        port_num = allocator.reservePort()
        assert(port_num != bad_port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((HOST, port_num))
            result = 0
        except: # pragma: no cover
            result = 1 # pragma: no cover
        sock.listen(1)
        assert(result == 0)
        available_ports.remove(port_num)
        sockets[port_num] = sock
        count += 1
        assert(count <= total_ports)
    
    # At this point, no ports should be left availble
    try:
        allocator.reservePort()
    except Exception as e:
        assert(isinstance(e, RuntimeError))

    # Release ports
    for port_num, sock in sockets.items():
        sock.close()
        allocator.releasePort(port_num)
        available_ports.add(port_num)
        count -= 1

    bad_sock.close()
    available_ports.add(bad_port)

    # We should be able to reserve the full set of available ports
    while len(available_ports) > 0:
        port_num = allocator.reservePort()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((HOST, port_num))
            sock.listen(1)
            result = 0
        except: # pragma: no cover
            result = 1 # pragma: no cover
        assert(result == 0)
        available_ports.remove(port_num)
        sockets[port_num] = sock
        count += 1
        assert(count <= total_ports)

    # At this point, all ports in the port block should be allocated, so
    # we should not be able to reserve another port
    try:
        allocator.reservePort()
    except Exception as e:
        assert(isinstance(e, RuntimeError))

    # Release the rest
    for port_num, sock in sockets.items():
        sock.close()
        allocator.releasePort(port_num)
        available_ports.add(port_num)
        count -= 1
    
    # Attempt to release port outside of range
    try:
        allocator.releasePort(start_port - 1)
    except Exception as e:
        assert(isinstance(e, RuntimeError))
    try:
        allocator.releasePort(end_port + 1)
    except Exception as e:
        assert(isinstance(e, RuntimeError))

    # Attempt to double free port
    try:
        allocator.releasePort(start_port)
    except Exception as e:
        assert(isinstance(e, RuntimeError))
    
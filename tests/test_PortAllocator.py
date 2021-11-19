from DataServer.portAllocator import PortAllocator
import socket
import os

def test_PortAllocator():
    start_port = 10200
    end_port = 10300
    allocator = PortAllocator(start_port, end_port)
    assert(allocator is not None)
    available_ports = set()
    HOST = '127.0.0.1'
    for port_num in range(start_port, end_port, 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((HOST, port_num))
            result = 0
        except:
            result = 1
        if result == 0:
            available_ports.add(port_num)
        else:
            print(f'Unable to open port {port_num}, error code {os.strerror(result)}')
        sock.close()
    assert(len(available_ports) != 0)
    sockets = {}
    total_ports = len(available_ports)
    count = 0
    while len(available_ports) > 0:
        port_num = allocator.reservePort()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((HOST, port_num))
            result = 0
        except:
            result = 1
        assert(result == 0)
        available_ports.remove(port_num)
        sockets[port_num] = sock
        count += 1
        assert(count <= total_ports)
    try:
        allocator.reservePort()
    except Exception as e:
        assert(isinstance(e, RuntimeError))
    bad_port = list(sockets.keys())[0]
    for port_num, sock in sockets.items():
        sock.close()
        allocator.releasePort(port_num)
        available_ports.add(port_num)
    bad_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    assert(bad_sock.connect_ex((HOST, bad_port)) == 0)
    available_ports.remove(bad_port)
    while len(available_ports) > 0:
        port_num = allocator.reservePort()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((HOST, port_num))
            result = 0
        except:
            result = 1
        sock.listen(1)
        assert(result == 0)
        available_ports.remove(port_num)
        sockets[port_num] = sock
        count += 1
        assert(count <= total_ports)
    try:
        allocator.reservePort()
    except Exception as e:
        assert(isinstance(e, RuntimeError))
    for port_num, sock in sockets.items():
        sock.close()
        allocator.releasePort(port_num)
        available_ports.add(port_num)

        
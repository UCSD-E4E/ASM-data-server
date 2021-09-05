from typing import Dict, Union
from DataServer import devices
import yaml
import os
import socket
import threading
import uuid
from asm_protocol import codec
import select

class ServerConfig:
    CONFIG_TYPES = {
        'data_dir': str,
        'port': int,
        'server_uuid': str
    }

    def __init__(self, path: str) -> None:
        with open(path, 'r') as config_stream:
            configDict = yaml.safe_load(config_stream)
            self.__load_config(configDict=configDict)

    def __load_config(self, configDict: Dict[str, Union[str, int, float]]):
        for key in self.CONFIG_TYPES:
            if key not in configDict:
                raise RuntimeError(f'Key "{key}" not found in configuration '
                                   'file!')
            if not isinstance(configDict[key], self.CONFIG_TYPES[key]):
                raise RuntimeError(f'Configuration key {key} is malformed!')
        self.data_dir = configDict['data_dir']
        assert(isinstance(self.data_dir, str))
        if not os.path.isdir(self.data_dir):
            raise RuntimeError(f'Data Directory path {self.data_dir} is '
                               'invalid!')

        self.port: int = int(configDict['port'])

        assert(isinstance(configDict['server_uuid'], str))
        self.uuid = uuid.UUID(configDict['server_uuid'])


class Server:
    def __init__(self, config_file: str, devices_file: str) -> None:
        self.config = ServerConfig(config_file)
        self.device_tree = devices.DeviceTree(devices_file)
        self.hostname = socket.gethostbyname('localhost')

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print(f"Binding to {self.hostname}:{self.config.port}")
            s.bind((self.hostname, self.config.port))
            s.listen()

            while True:
                client_socket, client_addr = s.accept()
                thread_args = {
                    'client_socket': client_socket,
                    'client_addr': client_addr
                }
                t = threading.Thread(target=self.client_thread, 
                                     kwargs=thread_args)
                t.start()

    def client_thread(self, client_socket: socket.socket,
                      client_addr):
        run = True
        protocol_codec = codec.Codec()
        with client_socket:
            client_socket.setblocking(False)
            while run:
                try:
                    data = client_socket.recv(65536)
                    if len(data):
                        packets = protocol_codec.decode(data)
                        print(packets)
                except BlockingIOError:
                    pass
                except Exception:
                    run = False
                    client_socket.close()

        print('Closed')

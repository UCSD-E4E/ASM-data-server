import asyncio
import datetime as dt
import os
import socket
import uuid
from asyncio.streams import StreamReader, StreamWriter
from threading import Event
from typing import Callable, Dict, List, Optional, Type, Union

import yaml
from asm_protocol import codec

from DataServer import devices


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


class ClientHandler:

    def __init__(self, device_tree: devices.DeviceTree, reader: StreamReader,
                 writer: StreamWriter) -> None:
        self.device_tree = device_tree
        self.reader = reader
        self.writer = writer
        self.protocol_codec = codec.Codec()
        self.end_event = Event()
        self.__packet_queue = asyncio.Queue()

        self._packet_handlers: Dict[Type[codec.binaryPacket],
                                    Callable[[codec.binaryPacket], None]] = \
            {
                codec.E4E_Heartbeat: self.heartbeat_handler
            }

        self.client_device: Optional[devices.Device] = None

    async def run(self):
        rx = asyncio.create_task(self.command_handler())
        tx = asyncio.create_task(self.response_sender())
        done, pending = await asyncio.wait({rx, tx}, timeout=3600)

        for task in pending:
            task.cancel()

    async def command_handler(self):
        while not self.end_event.is_set():
            data = await self.reader.read(65536)
            if len(data):
                packets = self.protocol_codec.decode(data)
                for packet in packets:
                    pass
            else:
                # Do this to unblock the response_sender
                await self.__packet_queue.put(None)
                self.end_event.set()
        print('Rx closed')

    async def response_sender(self):
        while not self.end_event.is_set():
            packet = await self.__packet_queue.get()
            if not packet:
                continue
            bytes_to_send = self.protocol_codec.encode([packet])
            self.writer.write(bytes_to_send)
            await self.writer.drain()
        self.writer.close()
        print('Tx closed')

    def heartbeat_handler(self, packet: codec.binaryPacket):
        client_uuid = packet._source
        if not self.client_device:
            self.client_device = self.device_tree.getDeviceByUUID(client_uuid)
        else:
            assert(self.client_device.uuid == client_uuid)
        self.client_device.setLastHeardFrom(dt.datetime.now())


class Server:
    def __init__(self, config_file: str, devices_file: str) -> None:
        self.config = ServerConfig(config_file)
        self.device_tree = devices.DeviceTree(devices_file)
        self.hostname = socket.gethostbyname('localhost')
        self.__client_queues: List[ClientHandler] = []

    async def run(self):
        server = await asyncio.start_server(self.client_thread, self.hostname,
                                            self.config.port)
        async with server:
            await server.serve_forever()

    async def client_thread(self, reader: StreamReader, writer: StreamWriter):
        client = ClientHandler(self.device_tree, reader, writer)
        self.__client_queues.append(client)
        await client.run()
        self.__client_queues.remove(client)

import asyncio
import datetime as dt
import os
import pathlib
import socketserver
import uuid
from asyncio.streams import StreamReader, StreamWriter
from threading import Event
from typing import (Awaitable, BinaryIO, Callable, Dict, List, Optional, Tuple,
                    Type, Union)

import yaml
from asm_protocol import codec

from DataServer import devices
import shutil

class ServerConfig:
    CONFIG_TYPES = {
        'data_dir': str,
        'port': int,
        'server_uuid': str,
        'video_increment': int
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
        if not isinstance(configDict['data_dir'], str):
            raise RuntimeError(f'Data Directory path {configDict["data_dir"]}'
                               ' is invalid!')
        self.data_dir = str(configDict['data_dir'])
        if not os.path.isdir(self.data_dir):
            raise RuntimeError(f'Data Directory path {self.data_dir} is '
                               'invalid!')

        self.port: int = int(configDict['port'])

        assert(isinstance(configDict['server_uuid'], str))
        self.uuid = uuid.UUID(configDict['server_uuid'])
        self.video_increment_s = int(configDict['video_increment'])


class ClientHandler:

    def __init__(self, device_tree: devices.DeviceTree, reader: StreamReader,
                 writer: StreamWriter, config: ServerConfig) -> None:
        self.device_tree = device_tree
        self.reader = reader
        self.writer = writer
        self.protocol_codec = codec.Codec()
        self.end_event = Event()
        self.__packet_queue: asyncio.Queue[Optional[codec.binaryPacket]] = \
            asyncio.Queue()

        self._packet_handlers: Dict[Type[codec.binaryPacket],
                                    Callable[[codec.binaryPacket],
                                             Awaitable[None]]] = \
            {
                codec.E4E_Heartbeat: self.heartbeat_handler,
                codec.E4E_START_RTP_CMD: self.onRTPStart
            }

        self.client_device: Optional[devices.Device] = None
        self._data_endpoints: Dict[Tuple[int, int], Optional[BinaryIO]] = {}

        self._config = config

        self.hasClient = asyncio.Event()
        
    async def run(self):
        rx = asyncio.create_task(self.command_handler())
        tx = asyncio.create_task(self.response_sender())
        done, pending = await asyncio.wait({rx, tx})

        for task in pending:
            task.cancel()

        for fi in self._data_endpoints.values():
            if fi:
                fi.close()

    async def command_handler(self):
        while not self.end_event.is_set():
            data = await self.reader.read(65536)
            if len(data):
                packets = self.protocol_codec.decode(data)
                for packet in packets:
                    if type(packet) in self._packet_handlers:
                        asyncio.create_task(self._packet_handlers[type(packet)](packet))
                    else:
                        print(f"no handler for class {type(packet)}")
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
            print(f'Sending {packet}')
            bytes_to_send = self.protocol_codec.encode([packet])
            self.writer.write(bytes_to_send)
            await self.writer.drain()
        self.writer.close()
        print('Tx closed')

    async def sendPacket(self, packet: codec.binaryPacket):
        try:
            await self.__packet_queue.put(packet)
        except Exception:
            print("Failed to queue packet")

    async def heartbeat_handler(self, packet: codec.binaryPacket):
        assert(isinstance(packet, codec.E4E_Heartbeat))
        client_uuid = packet._source
        if not self.client_device:
            print(f'getting client for uuid {client_uuid}')
            try:
                self.client_device = self.device_tree.getDeviceByUUID(client_uuid)
            except devices.DeviceNotFoundError as e:
                newDevice = devices.Device(client_uuid, "Auto-registered device", devices.DeviceType.AUTO_REGISTERED)
                self.device_tree.addDevice(newDevice)
                self.client_device = newDevice
                print(f"Added new device {newDevice}")
        else:
            assert(self.client_device.deviceID == client_uuid)
        print(f"Got heartbeat from {self.client_device.deviceID} "
              f"({self.client_device.description}) at {packet.timestamp}")
        self.client_device.setLastHeardFrom(dt.datetime.now())
        self.hasClient.set()

    async def onRTPStart(self, packet: codec.binaryPacket):
        print("Got RTP Start Command")
        assert(isinstance(packet, codec.E4E_START_RTP_CMD))
        with socketserver.TCPServer(('', 0), None) as s:
            free_port = s.server_address[1]
        print(f'Got port {free_port}')
        response = codec.E4E_START_RTP_RSP(self._config.uuid, packet._source,
                                           free_port, packet.streamID)
        proc = await self.runRTPServer(free_port)
        await self.sendPacket(response)
        await proc.wait()
        print("ffmpeg shutdown")

    async def runRTPServer(self, port: int):
        await self.hasClient.wait()
        assert(self.client_device)
        data_dir = self._config.data_dir

        device_path = self.client_device.getDevicePath()
        fname = '%Y.%m.%d.%H.%M.%S.mp4'
        file_path = os.path.abspath(os.path.join(data_dir, device_path, fname))
        file_dir = os.path.dirname(file_path)
        pathlib.Path(file_dir).mkdir(parents=True, exist_ok=True)
        
        cmd = (f'ffmpeg -i tcp://@:{port}?listen -c copy -flags +global_header'
               f' -f segment -segment_time {self._config.video_increment_s} -strftime 1 '
               f'-reset_timestamps 1 {file_path}')
        proc_out = asyncio.subprocess.PIPE
        proc_err = asyncio.subprocess.PIPE
        proc = await asyncio.create_subprocess_shell(cmd, stdout=proc_out,
                                                     stderr=proc_err)
        print(f'RTP Server on port {port} started outputting to {file_dir}')
        return proc

    async def data_packet_handler(self, packet: codec.binaryPacket):
        if self.client_device:
            file_key = (packet._class, packet._id)
            if file_key not in self._data_endpoints:
                self.open_file_endpoint(file_key)
            endpoint = self._data_endpoints[file_key]
            assert(endpoint)
            if endpoint.closed:
                self.open_file_endpoint(file_key)
            endpoint.write(self.protocol_codec.encode([packet]))

    def open_file_endpoint(self, file_key):
        assert(self.client_device)
        device_dir = self.client_device.getDevicePath()
        data_dir = self._config.data_dir
        fname = dt.datetime.now().strftime('%Y.%m.%d.%H.%M.%S.bin')
        file_path = os.path.abspath(os.path.join(data_dir, device_dir, fname))
        file_dir = os.path.dirname(file_path)
        pathlib.Path(file_dir).mkdir(parents=True, exist_ok=True)
        self._data_endpoints[file_key] = open(file_path, 'ab')


class Server:
    def __init__(self, config_file: str, devices_file: str) -> None:
        self.config = ServerConfig(config_file)
        self.device_tree = devices.DeviceTree(devices_file)
        self.hostname = ''
        self.__client_queues: List[ClientHandler] = []

    async def run(self):
        print(f'Connecting to {self.hostname}:{self.config.port}')
        server = await asyncio.start_server(self.client_thread, self.hostname,
                                            self.config.port)
        async with server:
            await server.serve_forever()

    async def client_thread(self, reader: StreamReader, writer: StreamWriter):
        client = ClientHandler(device_tree=self.device_tree, reader=reader,
                               writer=writer, config=self.config)
        self.__client_queues.append(client)
        await client.run()
        self.__client_queues.remove(client)

    def checkForServices(self):
        self.__checkForFFMPEG()

    def __checkForFFMPEG(self):
        if shutil.which('ffmpeg') is None:
            raise RuntimeError("Could not find ffmpeg")

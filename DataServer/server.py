import asyncio
import datetime as dt
import logging
import os
import pathlib
import shutil
import socketserver
import subprocess
import uuid
from asyncio.streams import StreamReader, StreamWriter
from threading import Event
from typing import (Any, Awaitable, BinaryIO, Callable, Dict, List, Optional,
                    Tuple, Type, Union)

import yaml
from asm_protocol import codec

import DataServer
from DataServer import devices
from DataServer.portAllocator import PortAllocator

import ASM_utils.ffmpeg.ffmpeg as ffmpeg
import ASM_utils.ffmpeg.rtp as rtp
import ASM_utils.ffmpeg.file as file_sink

class ServerConfig:
    CONFIG_TYPES = {
        'data_dir': str,
        'port': int,
        'server_uuid': str,
        'video_increment': int,
        'rtsp_port_block': list,
    }

    def __init__(self, path: str) -> None:
        self._log = logging.getLogger()
        with open(path, 'r') as config_stream:
            configDict = yaml.safe_load(config_stream)
            self.__load_config(configDict=configDict)

    def __load_config(self, configDict: Dict[str, Any]):
        for key in self.CONFIG_TYPES:
            if key not in configDict:
                raise RuntimeError(f'Key "{key}" not found in configuration '
                                   'file!')
            if not isinstance(configDict[key], self.CONFIG_TYPES[key]):
                raise RuntimeError(f'Configuration key {key} is malformed!')
            self._log.info(f'Discovered {key}: {configDict[key]}')
        if not isinstance(configDict['data_dir'], str):
            raise RuntimeError(f'Data Directory path {configDict["data_dir"]}'
                               ' is invalid!')
        self.data_dir = str(configDict['data_dir'])
        if not os.path.isdir(self.data_dir):
            raise RuntimeError(f'Data Directory path {self.data_dir} is '
                               'invalid!')
        self._log.info(f'Data Directory: {self.data_dir}')
        self.port: int = int(configDict['port'])

        assert(isinstance(configDict['server_uuid'], str))
        self.uuid = uuid.UUID(configDict['server_uuid'])
        self.video_increment_s = int(configDict['video_increment'])
        self.rtsp_ports = PortAllocator(configDict['rtsp_port_block'][0], configDict['rtsp_port_block'][1])


class ClientHandler:

    def __init__(self, device_tree: devices.DeviceTree, reader: StreamReader,
                 writer: StreamWriter, config: ServerConfig) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
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
        self._log.debug("Starting tasks")
        rx = asyncio.create_task(self.command_handler())
        tx = asyncio.create_task(self.response_sender())
        done, pending = await asyncio.wait({rx, tx})

        for task in pending:
            task.cancel()

        for fi in self._data_endpoints.values():
            if fi:
                fi.close()

    async def command_handler(self):
        logger = logging.getLogger("ClientHandler Receiver")
        logger.info("Started")
        while not self.end_event.is_set():
            data = await self.reader.read(65536)
            if len(data):
                packets = self.protocol_codec.decode(data)
                for packet in packets:
                    logger.info(f'Received {packet}')
                    if type(packet) in self._packet_handlers:
                        asyncio.create_task(self._packet_handlers[type(packet)](packet))
                    else:
                        self._log.warning(f'No handler for class {type(packet)}')
            else:
                # Do this to unblock the response_sender
                await self.__packet_queue.put(None)
                self.end_event.set()
        logger.info(f'Rx closed')

    async def response_sender(self):
        logger = logging.getLogger("ClientHandler Sender")
        logger.info("Started")
        while not self.end_event.is_set():
            packet = await self.__packet_queue.get()
            if not packet:
                continue
            logger.info(f'Sending Packet {packet}')
            bytes_to_send = self.protocol_codec.encode([packet])
            self.writer.write(bytes_to_send)
            await self.writer.drain()
        self.writer.close()
        logger.info('Tx closed')

    async def sendPacket(self, packet: codec.binaryPacket):
        log = logging.getLogger('ClientHandler I/O')
        try:
            await self.__packet_queue.put(packet)
            log.info(f'Queued packet {packet}')
        except Exception:
            log.exception('Failed to queue packet')

    async def heartbeat_handler(self, packet: codec.binaryPacket):
        assert(isinstance(packet, codec.E4E_Heartbeat))
        client_uuid = packet._source
        if not self.client_device:
            self._log.info(f'Getting client for uuid {client_uuid}')
            try:
                self.client_device = self.device_tree.getDeviceByUUID(client_uuid)
            except devices.DeviceNotFoundError as e:
                newDevice = devices.Device(client_uuid, "Auto-registered device", devices.DeviceType.AUTO_REGISTERED)
                self.device_tree.addDevice(newDevice)
                self.client_device = newDevice
                self._log.info(f"Added new device {newDevice}")
        else:
            assert(self.client_device.deviceID == client_uuid)
        self._log.info(f"Got heartbeat from {self.client_device.deviceID} "
              f"({self.client_device.description}) at {packet.timestamp}")
        self.client_device.setLastHeardFrom(dt.datetime.now())
        self.hasClient.set()

    async def onRTPStart(self, packet: codec.binaryPacket):
        SUFFIX_MAP = {
            1: self.startRTPVideoServer,
            2: self.startRTPAudioServer
        }
        self._log.info("Got RTP Start Command")
        assert(isinstance(packet, codec.E4E_START_RTP_CMD))
        free_port = self._config.rtsp_ports.reservePort()
        self._log.info(f'Got port {free_port}')
        response = codec.E4E_START_RTP_RSP(self._config.uuid, packet._source,
                                           free_port, packet.streamID)
        proc = await SUFFIX_MAP[packet.streamID](free_port)
        await self.sendPacket(response)
        retval = await proc.wait()
        self._config.rtsp_ports.releasePort(free_port)
        if retval != 0:
            self._log.warning("ffmpeg shut down with error code %d", retval)
            self._log.info("ffmpeg stderr: %s", (await proc.stderr.read()).decode())
            self._log.info("ffmpeg stdout: %s", (await proc.stdout.read()).decode())
        else:
            self._log.info("ffmpeg returned with code %d", retval)
    
    async def startRTPAudioServer(self, port: int):
        await self.hasClient.wait()
        assert(self.client_device)
        data_dir = self._config.data_dir

        device_path = self.client_device.getDevicePath()
        fname = '%Y.%m.%d.%H.%M.%S.mp3'
        file_path = pathlib.Path(data_dir, device_path, fname)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        segment_length = dt.timedelta(seconds=self._config.video_increment_s)

        stream_source = rtp.RTPAudioStream('@', port)
        
        stream_sink = file_sink.SegmentedAudioFileSink()
        stream_sink.setPath(pathlib.Path(file_path))
        stream_sink.set_segment_length(segment_length)
        stream_sink.configure_audio(codec='libmp3lame')

        stream_config = ffmpeg.FFMPEGInstance()
        stream_config.set_input(stream_source)
        stream_config.set_output(stream_sink)
        
        # cmd = (f'ffmpeg -i tcp://@:{port}?listen -c copy -flags +global_header'
        #        f' -f segment -segment_time {self._config.video_increment_s} -strftime 1 '
        #        f'-reset_timestamps 1 {file_path}')
        cmd = " ".join(stream_config.get_command())
        proc_out = asyncio.subprocess.PIPE
        proc_err = asyncio.subprocess.PIPE
        self._log.info(f'Started ffmpeg with command: {cmd}')
        proc = await asyncio.create_subprocess_shell(cmd, stdout=proc_out,
                                                     stderr=proc_err)
        self._log.info(f'RTP Audio Server on port {port} started outputting to {file_path.parent.as_posix()}')
        return proc

    async def startRTPVideoServer(self, port: int):
        await self.hasClient.wait()
        assert(self.client_device)
        data_dir = self._config.data_dir

        device_path = self.client_device.getDevicePath()
        fname = '%Y.%m.%d.%H.%M.%S.mp4'
        file_path = pathlib.Path(data_dir, device_path, fname)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        segment_length = dt.timedelta(seconds=self._config.video_increment_s)

        stream_source = rtp.RTPVideoStream('@', port)
        
        stream_sink = file_sink.SegmentedVideoFileSink()
        stream_sink.setPath(pathlib.Path(file_path))
        stream_sink.set_segment_length(segment_length)

        stream_config = ffmpeg.FFMPEGInstance()
        stream_config.set_input(stream_source)
        stream_config.set_output(stream_sink)
        
        # cmd = (f'ffmpeg -i tcp://@:{port}?listen -c copy -flags +global_header'
        #        f' -f segment -segment_time {self._config.video_increment_s} -strftime 1 '
        #        f'-reset_timestamps 1 {file_path}')
        cmd = " ".join(stream_config.get_command())
        proc_out = asyncio.subprocess.PIPE
        proc_err = asyncio.subprocess.PIPE
        self._log.info(f'Started ffmpeg with command: {cmd}')
        proc = await asyncio.create_subprocess_shell(cmd, stdout=proc_out,
                                                     stderr=proc_err)
        self._log.info(f'RTP Video Server on port {port} started outputting to {file_path.parent.as_posix()}')
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
        self._log.info(f'Opened file endpoint for {file_key} at {file_path}')


class Server:
    def __getRevision(self) -> str:
        try:
            git_rev_parse = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
        except subprocess.CalledProcessError as e:
            git_rev_parse = ''
        try:
            git_diff_ret = subprocess.run(['git', 'diff', '--quiet']).returncode
        except Exception as e:
            git_diff_ret = 0
        if git_diff_ret != 0:
            git_rev_parse += ' dirty'
        return git_rev_parse

    def __init__(self, config_file: str) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.info(f"Starting ASM Data Server v{DataServer.__version__}, {self.__getRevision()}")
        self.config = ServerConfig(config_file)
        devices_file = os.path.join(self.config.data_dir, 'devices.yaml')
        self.device_tree = devices.DeviceTree(devices_file)
        self.hostname = ''
        self.__client_queues: List[ClientHandler] = []

    async def run(self):
        self._log.info(f'Connecting to {self.hostname}:{self.config.port}')
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
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path is None:
            raise RuntimeError("Could not find ffmpeg")
        self._log.info(f'Found ffmpeg as {ffmpeg_path}')

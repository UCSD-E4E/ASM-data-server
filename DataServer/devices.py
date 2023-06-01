from __future__ import annotations
import datetime as dt
import enum
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
import pathlib

import yaml


class DeviceType(enum.Enum):
    ASM_REMOTE_SENSOR_UNIT = 'ASM_REMOTE_SENSOR_UNIT'
    ASM_ON_BOX_SENSOR_UNIT = 'ASM_ON_BOX_SENSOR_UNIT'
    UNKNOWN = "Unknown"
    AUTO_REGISTERED = 'AUTO_REGISTERED'

class DeviceNotFoundError(RuntimeError):
    def __init__(self, deviceID: uuid.UUID) -> None:
        self.deviceID = deviceID
        args = (f'Unable to find device id {deviceID}')
        super().__init__(*args)

@dataclass
class Device:
    deviceID: uuid.UUID
    description: str
    device_type: DeviceType
    fw_version: str = ""
    location: str = ""
    location_units: str = ""
    last_comms: Optional[dt.datetime] = None

    def getDevicePath(self):
        # if self.description:
        #     return f'{self.deviceID}_{self.description.replace(" ", "_")}'
        # else:
        return f'{self.deviceID}'

    def setLastHeardFrom(self, t: dt.datetime):
        self.last_comms = t

    @classmethod
    def from_dict(cls, deviceID: uuid.UUID, **kwargs) -> Device:
        dict_args = {
            'desc': '',
            'fw_ver': '',
            'location': '',
            'location_units': '',
            'type': ''
        }
        dict_args.update(kwargs)
        try:
            device_type = DeviceType(dict_args['type'])
        except ValueError:
            device_type = DeviceType.UNKNOWN
        return Device(
            deviceID=deviceID,
            description=str(dict_args['desc']),
            device_type=device_type,
            fw_version=str(dict_args['fw_ver']),
            location=str(dict_args['location']),
            location_units=str(dict_args['location_units']),
        )

    def to_dict(self) -> Dict[str, str]:
        dict_args = {
            'desc': self.description,
            'fw_ver': self.fw_version,
            'location': self.location,
            'location_units': self.location_units,
            'type': str(self.device_type.value)
        }
        return dict_args

class DeviceTree:
    def __init__(self, path: str):
        if not os.path.isfile(path):
            file_dir = os.path.dirname(path)
            pathlib.Path(file_dir).mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as stream:
                yaml.safe_dump({}, stream)
        with open(path, 'r') as stream:
            tree: Optional[Dict[str, Any]] = yaml.safe_load(stream)
        self.devices: Dict[uuid.UUID, Device] = {}
        if tree is None:
            return
        if not isinstance(tree, dict):
            raise RuntimeError("Unknown devices.yaml format")
        for id, args in tree.items():
            deviceID = uuid.UUID(id)
            device = Device.from_dict(deviceID=deviceID, **args)
            self.devices[deviceID] = device
        self.__path = path
        
    def saveToDisk(self) -> None:
        device_dict: Dict[str, Dict[str, str]] = {}
        for deviceID, device in self.devices.items():
            device_dict[str(deviceID)] = device.to_dict()
        with open(self.__path, 'w') as stream:
            yaml.safe_dump(device_dict, stream)

    def getDeviceByUUID(self, uuid: uuid.UUID) -> Device:
        if uuid not in self.devices:
            raise DeviceNotFoundError(uuid)
        device_node = self.devices[uuid]
        return device_node

    def addDevice(self, device: Device) -> None:
        self.devices[device.deviceID] = device
        self.saveToDisk()


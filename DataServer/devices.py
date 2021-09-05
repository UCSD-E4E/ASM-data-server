from typing import Optional
import yaml
import uuid
import enum


class DeviceType(enum.Enum):
    ASM_REMOTE_SENSOR_UNIT = 'ASM_REMOTE_SENSOR_UNIT'
    ASM_ON_BOX_SENSOR_UNIT = 'ASM_ON_BOX_SENSOR_UNIT'


class Device:
    def __init__(self, uuid: uuid.UUID, **kwargs):
        self.uuid = uuid

        self.desc: Optional[str] = None
        if 'desc' in kwargs:
            if not isinstance(kwargs['desc'], str):
                raise TypeError('Expected str for argument desc, got '
                                f'{type(kwargs["desc"])} instead')
            self.desc = kwargs['desc']

    def getDevicePath(self):
        if self.desc:
            return f'{self.uuid}_{self.desc.replace(" ", "_")}'
        else:
            return f'{self.uuid}'


class DeviceTree:
    def __init__(self, path: str):
        with open(path, 'r') as stream:
            self.__tree = yaml.safe_load(stream)

    def getDeviceByUUID(self, uuid: uuid.UUID) -> Device:
        device_node = self.__tree[str(uuid)]
        return Device(uuid, **device_node)

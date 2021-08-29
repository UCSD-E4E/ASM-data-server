import yaml
import uuid
import enum

class DeviceType(enum.Enum):
    ASM_REMOTE_SENSOR_UNIT = 'ASM_REMOTE_SENSOR_UNIT'
    ASM_ON_BOX_SENSOR_UNIT = 'ASM_ON_BOX_SENSOR_UNIT'

class Device:
    def __init__(self, uuid: uuid.UUID, **kwargs):
        pass


class DeviceTree:
    def __init__(self, path: str):
        with open(path, 'r') as stream:
            self.__tree = yaml.safe_load(stream)

    def getDeviceByUUID(self, uuid: uuid.UUID) -> Device:
        device_node = self.__tree[str(uuid)]
        return Device(uuid, **device_node)

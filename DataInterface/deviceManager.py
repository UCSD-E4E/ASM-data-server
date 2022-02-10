import os
import appdirs
import yaml
import pathlib
import enum
from device import Device, OnBoxDevice, RemoteSensorDevice

class DeviceManager:
    app_name = 'ASMDataServer'
    app_author = 'E4E'

    dict_args = {
        'desc': '',
        'fw_ver': '',
        'location': '',
        'location_units': '',
        'type': ''
    }
    
    device_type = {
        'remote_sensor': 'ASM_REMOTE_SENSOR_UNIT',
        'on_box_sensor': 'ASM_ON_BOX_SENSOR_UNIT',
        'unknown': "Unknown",
        'auto_registered': 'AUTO_REGISTERED'
    }

    def __init__(self):
        # Get config filepath
        site_config = os.path.join(appdirs.site_config_dir(
            self.app_name, self.app_author), 'asm_config.yaml')
        user_config = os.path.join(appdirs.user_config_dir(
            self.app_name, self.app_author), 'asm_config.yaml')
        config_path = ""
        try:
            if os.path.isfile(site_config):
                config_path = site_config
            elif os.path.isfile(user_config):
                config_path = user_config
            else:
                config_path = pathlib.Path(__file__).parents[1].absolute() + 'asm_config.yaml'
        except Exception:
            raise RuntimeError("Config file \"asm_config.yaml\" not found")
        
        # Get server data datapath
        self.device_list = []
        with open(config_path, 'r') as config_stream:
            config_dict = yaml.safe_load(config_stream)
            if not isinstance(config_dict['data_dir'], str):
                raise RuntimeError(f'Data Directory path {config_dict["data_dir"]}'
                                    ' is invalid!')
            self.data_dir = str(config_dict['data_dir'])

        # Create Device objects
        self.device_list = []
        self.remote_sensor_device = None
        self.on_box_device = None
        with open(self.data_dir, 'r') as device_stream:
            device_info_dict = yaml.safe_load(device_stream)
            for id, device_info in device_info_dict:
                if device_info['type'] == self.device_type['remote_sensor']:
                    device = OnBoxDevice(uuid=id,
                                desc=device_info['desc'],
                                fw_ver=device_info['fw_ver'],
                                loc=device_info['location'],
                                loc_units=device_info['location_units'],
                                type=device_info['type'],
                                datapath=self.data_dir + str(id),
                                labelpath="8124cb7c-41ec-11ec-aaad-e45f015ed519")
                    self.remote_sensor_device = device
                elif device_info['type'] == self.device_type['on_box_sensor']:
                    device = RemoteSensorDevice(uuid=id,
                                desc=device_info['desc'],
                                fw_ver=device_info['fw_ver'],
                                loc=device_info['location'],
                                loc_units=device_info['location_units'],
                                type=device_info['type'],
                                datapath=self.data_dir + str(id))
                    self.on_box_device = device
                else:
                    device = Device(uuid=id,
                                desc=device_info['desc'],
                                fw_ver=device_info['fw_ver'],
                                loc=device_info['location'],
                                loc_units=device_info['location_units'],
                                type=device_info['type'],
                                datapath=self.data_dir + str(id))
                self.device_list.append(device)

    

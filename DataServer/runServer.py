import asyncio
import logging
import logging.handlers
import os
import pathlib
import time

import appdirs

from DataServer.server import Server
from DataServer.devices import Device

def main():
    os.environ['XDG_CONFIG_DIRS'] = '/usr/local/etc'
    app_name = 'ASMDataServer'
    app_author = 'E4E'

    if os.getuid() == 0:
        log_dest = os.path.join('var', 'log', 'asm_server.log')
    else:
        log_dir = appdirs.user_log_dir(app_name)
        pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_dest = os.path.join(log_dir, 'asm_server.log')

    print(f"Logging to {log_dest}")
    root_logger = logging.getLogger()
    # Log to root to begin
    root_logger.setLevel(logging.DEBUG)

    log_file_handler = logging.handlers.RotatingFileHandler(log_dest, maxBytes=5*1024*1024, backupCount=5)
    log_file_handler.setLevel(logging.DEBUG)

    root_formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    log_file_handler.setFormatter(root_formatter)
    root_logger.addHandler(log_file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARN)

    error_formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(error_formatter)
    root_logger.addHandler(console_handler)
    logging.Formatter.converter = time.gmtime

    def report_outage(device: Device):
        root_logger.warn(f'There was an outage: device {device.deviceID} went offline')

    site_config = os.path.join(appdirs.site_config_dir(
        app_name, app_author), 'asm_config.yaml')
    user_config = os.path.join(appdirs.user_config_dir(
        app_name, app_author), 'asm_config.yaml')
    try:
        if os.path.isfile(site_config):
            server = Server(site_config, report_outage)
        elif os.path.isfile(user_config):
            server = Server(user_config, report_outage)
        else:
            server = Server('asm_config.yaml')
    except Exception as e:
        root_logger.exception(f"Failed to create server: {e}")
        return
    try:
        asyncio.run(server.run())
    except Exception as e:
        root_logger.exception(f"Failed to run server: {e}")
        
if __name__ == "__main__":
    main()

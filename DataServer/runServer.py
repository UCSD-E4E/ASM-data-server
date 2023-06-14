import asyncio
import logging
import logging.handlers
import os
import pathlib
import time

import appdirs
from ASM_utils.logging import configure_logging

from DataServer.server import Server


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
    configure_logging()
    root_logger = logging.getLogger()

    site_config = os.path.join(appdirs.site_config_dir(
        app_name, app_author), 'asm_config.yaml')
    user_config = os.path.join(appdirs.user_config_dir(
        app_name, app_author), 'asm_config.yaml')
    try:
        if os.path.isfile(site_config):
            server = Server(site_config)
        elif os.path.isfile(user_config):
            server = Server(user_config)
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
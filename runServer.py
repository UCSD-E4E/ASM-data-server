import asyncio
from DataServer.server import Server
import os
import appdirs

if __name__ == "__main__":
    os.environ['XDG_CONFIG_DIRS'] = '/usr/local/etc'
    app_name = 'ASMDataServer'
    app_author = 'E4E'

    site_config = os.path.join(appdirs.site_config_dir(
        app_name, app_author), 'asm_config.yaml')
    if os.path.isfile(site_config):
        site_data = os.path.join(appdirs.site_data_dir(
            appname=app_name, appauthor=app_author), 'devices.yaml')

        server = Server(site_config, site_data)
    else:
        server = Server('asm_config.yaml', 'devices.yaml')
    asyncio.run(server.run())

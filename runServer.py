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
    user_config = os.path.join(appdirs.user_config_dir(
        app_name, app_author), 'asm_config.yaml')
    if os.path.isfile(site_config):
        server = Server(site_config)
    elif os.path.isfile(user_config):
        server = Server(user_config)
    else:
        server = Server('asm_config.yaml')
    asyncio.run(server.run())

# ASM-data-server
Aye-Aye Sleep Monitoring Project: Data Server Code

This project is currently inactive.  If you are interested in contributing to this project, please contact Engineers for Exploration at e4e@ucsd.edu.

# Instructions to Run
## Development
1. Open this repository as a VS Code Workspace
2. Use the Run and Debug menu to execute the server.
3. In this mode, the server will log to the user log directory.  On Linux, this is usually `${HOME}/.cache/ASMDataServer/asm_server.log`.
## Deployment
1. Run `sudo ./install.sh`
    1. If the default Python interpreter is not at least Python3.7, you may need to specify a different Python interpreter.  Use the `-p` flag to specify the absolute path to the desired interpreter.  For example, `sudo ./install.sh -p /usr/bin/python3.7`.  If this is done, it may also be necessary to specify the install location of the `runServer.py` script using the `-r` flag, for example, `sudo ./install.sh -p /home/asm-data/anaconda/envs/asm_dep/bin/python3 -r /home/asm-data/anaconda/envs/asm_dep/scripts/runServer.py`
2. Run `sudo service asm_server restart`
3. In this mode, the server will log to the system log directory.  On Linux, this is usually `/var/log/asm_server.log`.

# Configuration Files
1. The Data Server will search the following locations for the `asm_config.yaml` configuration file:
    - `/usr/local/etc/ASMDataServer/asm_config.yaml`
    - `'${HOME}/.config/ASMDataServer/asm_config.yaml`
    - `${CWD}`

#!/bin/bash
DEBUG=0
PYTHON=/usr/bin/python3
SERVICE_LOCATION=/lib/systemd/system
USER_MODE=
CONFIG_DIR=/usr/local/etc/ASMDataServer


usage() {
    echo "${0} usage: "
    echo "    -d            Specify debug"
    echo "    -p python     Specify python interpreter"
    echo "    -r runServer  Specify runServer.py location"
    echo "    -h            Display this message"
}

while getopts ":dp:U" arg; do
    case $arg in
        d)
            DEBUG=1
            ;;
        p)
            PYTHON=${OPTARG}
            ;;
        U)
            SERVICE_LOCATION=$HOME/.config/systemd/user
            mkdir -p ${SERVICE_LOCATION}
            USER_MODE=--user
            CONFIG_DIR=$HOME/.config
            ;;
        *)
            usage
            ;;        
    esac
done

if [[ $USER_MODE == '' ]]; then
    if [ $EUID != 0 ]; then
        sudo "$0" "$@"
        exit $?
    fi
fi

if [[ ${DEBUG} -eq 1 ]]; then
    ${PYTHON} -m pip install -e .
else
    ${PYTHON} -m pip install .
fi
RUN_SERVER=$(which runServer.py)
echo ${RUN_SERVER}
PYTHONESC=$(echo ${PYTHON} | sed 's/\//\\\//g')
RUN_SERVERESC=$(echo ${RUN_SERVER} | sed 's/\//\\\//g')
if [[ ${DEBUG} -eq 0 ]]
then
    
    if [ ! -f ${CONFIG_DIR}/asm_config.yaml ]
    then
        cp sample-config.yaml ${CONFIG_DIR}/asm_config.yaml
    fi
    
    cat asm_server.service | sed -e "s/python/${PYTHONESC}/g" | sed -e "s/runServer.py/${RUN_SERVERESC}/g" > ${SERVICE_LOCATION}/asm_server.service
    chmod 644 ${SERVICE_LOCATION}/asm_server.service
    systemctl ${USER_MODE} daemon-reload
    echo ${USER_MODE}
    systemctl ${USER_MODE} enable asm_server.service
    systemctl ${USER_MODE} start asm_server.service

fi
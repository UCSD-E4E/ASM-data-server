#!/bin/bash
DEBUG=0
PYTHON=/usr/bin/python3

if [ $EUID != 0 ]; then
    sudo "$0" "$@"
    exit $?
fi

usage() {
    echo "${0} usage: "
    echo "    -d          Specify debug"
    echo "    -p python   Specify python interpreter"
    echo "    -h          Display this message"
}

while getopts ":dp:" arg; do
    case $arg in
        d)
            DEBUG=1
            ;;
        p)
            PYTHON=${OPTARG}
            ;;
        *)
            usage
            ;;        
    esac
done

if [[ ${DEBUG} -eq 1 ]]; then
    ${PYTHON} -m pip install -e .
else
    ${PYTHON} -m pip install .
fi
PYTHONESC=$(echo ${PYTHON} | sed 's/\/\\\//g')
if [[ ${DEBUG} -eq 0 ]]
then
    
    if [ ! -f /usr/local/etc/asm_config.yaml ]
    then
        cp sample-config.yaml /usr/local/etc/asm_config.yaml
    fi
    
    cat asm_server.service | sed -e "s/python/${PYTHONESC}/g" > /lib/systemd/system/asm_server.service
    chmod 644 /lib/systemd/system/asm_server.service
    systemctl daemon-reload
    systemctl enable asm_server.service
    service asm_server start

fi
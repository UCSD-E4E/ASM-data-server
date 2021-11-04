#!/bin/bash
DEBUG=0

if [ $EUID != 0 ]; then
    sudo "$0" "$@"
    exit $?
fi

usage() {
    echo "${0} usage: "
    echo "    -d    Specify debug"
    echo "    -h    Display this message"
}

while getopts ":d" arg; do
    case $arg in
        d)
            DEBUG=1
            ;;
        *)
            usage
            ;;        
    esac
done

if [[ ${DEBUG} -eq 1 ]]; then
    python3 -m pip install -e .
else
    python3 -m pip install .
fi

if [[ ${DEBUG} -eq 0 ]]
then
    
    if [ ! -f /usr/local/etc/asm_config.yaml ]
    then
        cp sample-config.yaml /usr/local/etc/asm_config.yaml
    fi
    
    cp asm_server.service /lib/systemd/system/asm_server.service
    chmod 644 /lib/systemd/system/asm_server.service
    systemctl daemon-reload
    systemctl enable asm_server.service
    systemctl asm_server.service start

fi
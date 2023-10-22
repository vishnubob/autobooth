#!/bin/bash

PHOTOBOOTH_ROOT="/home/ghall/code/autobooth"

# Check if at least one argument is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <service_name>"
    exit 1
fi

service_name=$1
if [ -e "$PHOTOBOOTH_ROOT/venv/bin/activate" ]; then
    source $PHOTOBOOTH_ROOT/venv/bin/activate
fi
cd $PHOTOBOOTH_ROOT

# Validate service name
case $service_name in
    speech|camera|transcribe|display|presence)
        # Start the corresponding service
        python3 -m src.services.$service_name
        ;;
    *)
        # Invalid service name provided
        echo "Error: Unknown service name '$service_name'. Supported services are: speech, camera, transcribe, display, presence"
        exit 2
        ;;
esac




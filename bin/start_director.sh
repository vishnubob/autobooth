#!/bin/bash

PHOTOBOOTH_ROOT="/home/ghall/code/autobooth"

if [ -e "$PHOTOBOOTH_ROOT/venv/bin/activate" ]; then
    source $PHOTOBOOTH_ROOT/venv/bin/activate
fi
cd $PHOTOBOOTH_ROOT

# start photobooth director
python -m src.director

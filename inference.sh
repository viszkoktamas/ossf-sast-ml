#!/bin/bash

if [ -d $(dirname $0)/inference/venv ]; then
  source $(dirname $0)/inference/venv/bin/activate
fi

if [ -z "$2" ]; then
    python $(dirname $0)/inference/inference.py -i $1
else
    if [ -z "$3" ]; then
        python $(dirname $0)/inference/inference.py -i $1 -m $2
    else
        python $(dirname $0)/inference/inference.py -i $1 -m $2 -r $3
    fi
fi

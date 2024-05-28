#!/bin/bash

python3 -m venv inference/venv
source inference/venv/bin/activate
pip install -r inference/requirements.txt

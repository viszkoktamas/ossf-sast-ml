#!/bin/bash

pip install virtualenv
python -m venv inference/venv
source inference/venv/bin/activate
pip install -r inference/requirements.txt

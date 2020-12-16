#!/bin/bash

python3 -m virtualenv -p python3 env
source env/bin/activate
pip install -r requirements.txt

sudo ./setup.py
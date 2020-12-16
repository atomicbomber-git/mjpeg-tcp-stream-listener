#!/usr/bin/python3

import os
from os import path
import re

script_dir = os.path.dirname(os.path.realpath(__file__))

name = input("Type your desired config name for this project: ")
name = re.sub(r'\W+', '', name)

os.system("mkdir -p /var/log/{}".format(name))
os.system("touch /var/log/{}/error.log".format(name))
os.system("touch /var/log/{}/output.log".format(name))

with open("/etc/supervisor/conf.d/{}.conf".format(name), "w") as config_file:
    for line in open("supervisord.conf.example", "r"):
        line = re.sub("<PROJECT_NAME>", name, line)
        line = re.sub("<PROJECT_PATH>", script_dir, line)  
        config_file.write(line)

os.system("supervisorctl reread")
os.system("supervisorctl start {}".format(name))
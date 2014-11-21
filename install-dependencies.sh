#! /bin/bash

# Make sure only root can run our script
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

# arp-scan
apt-get -y install arp-scan

# python zeroMQ libraries
apt-get -y install python-zmq
apt-get -y install python-pip
pip install pyzmq

# spark-cli
apt-get -y install nodejs
apt-get -y install nodejs-legacy
apt-get -y install npm
npm install -g spark-cli

# Prompt for spark login
spark cloud login


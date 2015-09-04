#! /bin/bash

# Make sure only root can run our script
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

apt-get update

# arp-scan
apt-get -y install arp-scan

# python psutil
apt-get -y install python-psutil

# python zeroMQ libraries
apt-get -y install python-zmq

apt-get -y remove python-pip
wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
python get-pip.py
rm get-pip.py 

pip install pyzmq
pip install twilio

# python requests (for spark REST api)
pip install requests --upgrade

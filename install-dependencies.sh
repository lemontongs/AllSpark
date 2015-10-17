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

# Graphite for data logging
apt-get -y install graphite-carbon
apt-get -y install python-django

# Apache
apt-get -y install apache2 libapache2-mod-wsgi


# Get pip
apt-get -y remove python-pip
wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
python get-pip.py
rm get-pip.py

pip install pyzmq
pip install twilio
pip install graphite-web
pip install django-tagging==0.3.6
pip install pyparsing

#
# Configure Graphite
#
# TODO: add time zone to /opt/graphite/webapp/graphite/local_settings.py
cd /opt/graphite/webapp/graphite/
python manage.py syncdb
cp local_settings.py.example local_settings.py
cd -

cp /opt/graphite/conf/graphite.wsgi.example /opt/graphite/conf/graphite.wsgi
cp /opt/graphite/examples/example-graphite-vhost.conf /etc/apache2/sites-available/

cd /etc/apache2/sites-enabled/
ln -s ../sites-available/example-graphite-vhost.conf
cd -


# python requests (for spark REST api)
pip install requests --upgrade

# Start apache
service apache2 restart

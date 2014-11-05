#! /bin/bash

# Only root can run this script
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

python spark_thermostat_html_builder.py > log 2>&1 &


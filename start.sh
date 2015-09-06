#! /bin/bash

# Only root can run this script
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

#
# Remove null bytes from files. These occure when the system is shut down abruptly.
#
#for i in `ls data/*.csv`
#do
#    tr < $i -d '\000' > $i
#done

# Start
python -u spark_thermostat_html_builder.py > logs/log 2>&1 &


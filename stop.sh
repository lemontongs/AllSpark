#! /bin/bash

# Only root can run this script
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

spark_pid=`ps -elf | grep spark_thermostat_html_builder.py | grep -v "grep" | awk '{print $4}'`

if [[ $spark_pid -eq "" ]]; then
    echo "Not running"
    exit 0
fi

echo $spark_pid

kill -9 $spark_pid

rm *.pyc


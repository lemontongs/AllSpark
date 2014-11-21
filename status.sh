#! /bin/bash

spark_pid=`ps -elf | grep spark_thermostat_html_builder.py | grep -v "grep" | awk '{print $4}'`

if [[ $spark_pid -eq "" ]]; then
    echo "Not running"
    exit 0
fi

echo $spark_pid


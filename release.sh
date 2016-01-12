#! /bin/bash


VERSION=`git rev-parse --short HEAD`
FILENAME=spark_latest

if [[ -e $FILENAME ]]
then
    rm $FILENAME
fi

echo $VERSION > $FILENAME

scp $FILENAME rpi2:/var/www/$FILENAME

rm $FILENAME


#! /bin/bash


VERSION=`git rev-parse --short HEAD`
FILENAME=allspark_latest

if [[ -e $FILENAME ]]
then
    rm $FILENAME

fi

echo $VERSION
echo $VERSION > $FILENAME

scp $FILENAME rpi2:/var/www/$FILENAME

rm $FILENAME


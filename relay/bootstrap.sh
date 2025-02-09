#!/bin/bash
set -e
LOG="/home/bootstrap.log"
cd /home

service tor start 
service tor status 

#service privoxy start 2>&1 | tee -ia $LOG
#service privoxy status | tee -ia $LOG
#echo bridges:
#grep "Bridge " /etc/tor/torrc
tail -f /var/log/tor/info.log
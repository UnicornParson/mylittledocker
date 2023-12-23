#!/bin/bash
LOG="/home/bootstrap.log"
cd /home
#python3 -c "import scanner; scanner.main()" --torrc -o relays.txt
#cp /etc/tor/torrc.orig /etc/tor/torrc
#curl -o relays.txt http://192.168.0.22/bridges_rc.txt
#cat relays.txt >> /etc/tor/torrc
#cat /etc/tor/torrc
service tor start 2>&1 | tee -ia $LOG
service tor status | tee -ia $LOG

#service privoxy start 2>&1 | tee -ia $LOG
#service privoxy status | tee -ia $LOG
#echo bridges:
#grep "Bridge " /etc/tor/torrc
top
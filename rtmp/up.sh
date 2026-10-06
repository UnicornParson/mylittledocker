#!/bin/bash

set -e
echo 1
source ./.env
sudo chmod -R 777 ${RTMP_HOME}/live
sudo chmod -R 777 ${RTMP_HOME}/log
docker compose up -d --build --force-recreate

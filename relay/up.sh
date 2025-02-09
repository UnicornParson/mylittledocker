#!/bin/bash
source ./.env
echo "TOR_CONFIG: $TOR_CONFIG"
echo "TOR_DATA: $TOR_DATA"
mkdir -p $TOR_CONFIG
mkdir -p $TOR_DATA

docker-compose up  --build --force-recreate
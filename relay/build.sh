#!/bin/bash
source ./.env
docker build --no-cache --progress plain -t relay .
#!/bin/bash
docker build -f Dockerfile.24.10 --no-cache --progress plain -t jupyter24 .
#docker build -f Dockerfile.24.10 --progress plain -t jupyter24 .
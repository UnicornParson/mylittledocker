#!/bin/bash
echo $PWD/moonland
docker run --name moonland -p 25565:25565 -v $PWD/moonland/:/home/moonland/ moonland:latest
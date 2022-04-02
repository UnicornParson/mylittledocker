#!/bin/bash

docker build -t moonland . 2>&1 | tee -i build.log
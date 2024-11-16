#!/bin/bash
LOG="/home/bootstrap.log"
#ipcluster start -n 16 --daemonize
cd /home
#python3 -m http.server 8000 &
#~/_venv/bin/jupyter notebook --port=8001 --no-browser --ip=0.0.0.0 --allow-root
##/root/.jupyter/jupyter_notebook_config.py
~/_venv/bin/jupyter lab notebook --port=8001 --no-browser --ip=0.0.0.0 --allow-root
/bin/bash
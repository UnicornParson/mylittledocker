FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && apt upgrade -y
RUN apt-get update && apt install -y linux-libc-dev software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update && apt install -y \
nano \
htop \
openssh-server \
curl \
perl \
libnet-ssleay-perl \
openssl \
libauthen-pam-perl \
libpam-runtime \
libio-pty-perl

RUN apt-get update && apt install -y \
unzip \
gcc \
gawk \
g++ \
build-essential \
libcap-dev \
libxml2-dev \
libssl-dev \
net-tools \
git-all \
python3-psycopg2 \
pandoc texlive-xetex texlive-fonts-recommended texlive-plain-generic


RUN apt-get update && apt install -y python3-pip python3.10-dev && python3.10 -m pip install --upgrade pip
RUN python3.10 -m pip install \
numpy \
pandas \
jupyter \
pympler \
ipyparallel \
jupyter_server \
asyncio \
tensorflow \
pytesseract \
opencv-python \
matplotlib \
matplotlib-inline \
line_profiler \
youtube-dl \
pymongo \
reprint \
line_profiler \
ffmpeg-quality-metrics \
nbconvert \
pyppeteer

RUN jupyter notebook --generate-config && \
jupyter nbextension install --py ipyparallel && \
jupyter nbextension enable --py ipyparallel && \
jupyter serverextension enable --py ipyparallel

RUN ipython profile create
COPY cfg/jupyter_notebook_config.py /root/.jupyter/jupyter_notebook_config.py
COPY cfg/ipython_config.py /root/.ipython/profile_default/ipython_config.py
# empty password
COPY cfg/jupyter_notebook_config.json /root/.jupyter/jupyter_notebook_config.json

COPY bootstrap.sh /home/bootstrap.sh
EXPOSE 8000
EXPOSE 8001
ENTRYPOINT ["/bin/bash", "/home/bootstrap.sh"]




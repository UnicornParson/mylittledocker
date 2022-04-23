FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && apt upgrade -y
RUN apt-get update && apt install -y linux-libc-dev
RUN apt install -y \
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

RUN apt install -y \
unzip \
gcc \
gawk \
g++ \
build-essential \
libcap-dev \
libxml2-dev \
libssl-dev \
libmbedcrypto3 \
libmbedtls12 \
libmbedx509-0 \
net-tools \
git-all

RUN apt update && apt install -y python3-psycopg2


RUN cd /home && wget http://prdownloads.sourceforge.net/webadmin/webmin_1.990_all.deb && dpkg -i webmin_1.990_all.deb && service webmin start
EXPOSE 10000
RUN apt install -y python3-pip python3-dev && python3 -m pip install --upgrade pip
RUN python3 -m pip install \
numpy \
pandas \
jupyter \
pympler \
ipyparallel \
jupyter_server \
asyncio \
tensorflow \
pytesseract \
opencv-python

RUN jupyter notebook --generate-config && \
jupyter nbextension install --py ipyparallel && \
jupyter nbextension enable --py ipyparallel && \
jupyter serverextension enable --py ipyparallel


COPY cfg/jupyter_notebook_config.py /root/.jupyter/jupyter_notebook_config.py
# empty password
COPY cfg/jupyter_notebook_config.json /root/.jupyter/jupyter_notebook_config.json
COPY bootstrap.sh /home/bootstrap.sh
EXPOSE 8000
EXPOSE 8001
ENTRYPOINT ["/bin/bash", "/home/bootstrap.sh"]




FROM ubuntu:latest
ENV DEBIAN_FRONTEND=noninteractive
#RUN add-apt-repository main && add-apt-repository universe && add-apt-repository restricted && add-apt-repository multiverse  
RUN apt update && apt upgrade -y

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
libio-pty-perl \
unzip \
gcc \
gawk \
g++ \
build-essential \
libcap-dev \
libxml2-dev \
libssl-dev \
tor \
net-tools \
obfs4proxy \
nyx
#libmbedcrypto3 \
#libmbedtls12 \
#libmbedx509-0

RUN apt install -y python3-pip python3-dev && python3 -m pip install --upgrade pip
RUN python3 -m pip install requests asyncio

# setup relay
#COPY cfg/torrc /etc/tor/torrc
#COPY cfg/torrc /etc/tor/torrc.orig
RUN service tor start
EXPOSE 9050

#RUN cd /home && wget https://www.privoxy.org/sf-download-mirror/Debian/3.0.33%20%28stable%29%20bullseye/privoxy_3.0.33-1~pp%2B1_amd64.deb && dpkg -i privoxy_3.0.33-1~pp+1_amd64.deb
#COPY cfg/privoxy.config /etc/privoxy/config
#EXPOSE 8118

COPY bootstrap.sh /home/bootstrap.sh
ENTRYPOINT ["/bin/bash", "/home/bootstrap.sh"]




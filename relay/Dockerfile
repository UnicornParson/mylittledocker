FROM ubuntu:latest
#FROM ubuntu:24.10
ENV DEBIAN_FRONTEND=noninteractive
USER root

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

HEALTHCHECK --interval=300s --timeout=15s --start-period=60s  \
    CMD curl -sS -x socks5h://127.0.0.1:9050 'https://check.torproject.org/api/ip' | grep -qm1 -E '"IsTor"\s*:\s*true'


VOLUME ["/etc/tor/torrc"]
EXPOSE 9050

#USER tor
COPY bootstrap.sh /home/bootstrap.sh
ENTRYPOINT ["/bin/bash", "/home/bootstrap.sh"]





FROM  ubuntu:21.10
ENV DEBIAN_FRONTEND=noninteractive
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
libmbedcrypto3 \
libmbedtls12 \
libmbedx509-0 \
openjdk-16-jre
EXPOSE 25565
RUN mkdir -p /home/moonland
COPY bootstrap.sh /home/bootstrap.sh
VOLUME /home/moonland
ENTRYPOINT ["/bin/bash", "/home/bootstrap.sh"]


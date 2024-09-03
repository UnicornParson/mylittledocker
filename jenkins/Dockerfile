FROM jenkins/jenkins:jdk17
USER root
RUN useradd -m ed 

RUN apt update && apt install -y emacs nano wget
RUN apt update && apt install -y git 
RUN apt update && apt install -y build-essential libssl-dev zlib1g-dev libbz2-dev ninja-build cmake
RUN apt update && apt install -y htop python3.11-full python3.11-venv python3-pip python-is-python3 ffmpeg  python3-openssl
RUN apt update && apt install -y pypy3-dev 
RUN apt update && apt install -y meson binutils make csh g++ sed gawk autoconf automake autotools-dev pkg-config libtool yasm gnutls-bin
RUN curl -L https://yt-dl.org/downloads/latest/youtube-dl -o /usr/local/bin/youtube-dl && chmod a+rx /usr/local/bin/youtube-dl

#USER jenkins

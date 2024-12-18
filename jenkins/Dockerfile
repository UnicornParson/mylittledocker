FROM jenkins/jenkins:jdk17
USER root
RUN useradd -m ed 

RUN apt update && apt install -y emacs nano wget
RUN apt update && apt install -y git 
RUN apt update && apt install -y build-essential libssl-dev zlib1g-dev libbz2-dev ninja-build cmake fakeroot ncurses-dev xz-utils  bc flex libelf-dev bison
RUN apt update && apt install -y htop python3.11-full python3.11-venv python3-pip python-is-python3 ffmpeg  python3-openssl
RUN apt update && apt install -y pypy3-dev 
RUN apt update && apt install -y meson binutils make csh g++ sed gawk autoconf automake autotools-dev pkg-config libtool yasm gnutls-bin linux-source zstd
RUN curl -L https://github.com/ytdl-org/ytdl-nightly/releases/download/2024.08.07/youtube-dl -o /usr/local/bin/youtube-dl && chmod a+rx /usr/local/bin/youtube-dl
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux -o /usr/local/bin/yt && chmod a+rx /usr/local/bin/yt

#USER jenkins

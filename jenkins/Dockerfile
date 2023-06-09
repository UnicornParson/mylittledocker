FROM jenkins/jenkins:latest
USER root
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
libio-pty-perl \
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
pandoc texlive-xetex \
texlive-fonts-recommended \
texlive-plain-generic \
ffmpeg \
p7zip \
golang


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



RUN go install github.com/gopherdata/gophernotes@v0.7.5
RUN mkdir -p ~/.local/share/jupyter/kernels/gophernotes
RUN cd ~/.local/share/jupyter/kernels/gophernotes
RUN cp "$(go env GOPATH)"/pkg/mod/github.com/gopherdata/gophernotes@v0.7.5/kernel/*  "."
RUN chmod +w ./kernel.json
RUN sed "s|gophernotes|$(go env GOPATH)/bin/gophernotes|" < kernel.json.in > kernel.json

EXPOSE 8080





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
COPY cfg/requirements.txt /root/requirements.txt
RUN python3.10 -m pip install -r /root/requirements.txt

RUN jupyter notebook --generate-config && \
jupyter nbextension install --py ipyparallel && \
jupyter nbextension enable --py ipyparallel && \
jupyter serverextension enable --py ipyparallel

RUN ipython profile create
COPY cfg/jupyter_notebook_config.py /root/.jupyter/jupyter_notebook_config.py
COPY cfg/ipython_config.py /root/.ipython/profile_default/ipython_config.py
# empty password
COPY cfg/jupyter_notebook_config.json /root/.jupyter/jupyter_notebook_config.json


RUN go install github.com/gopherdata/gophernotes@v0.7.5
RUN mkdir -p ~/.local/share/jupyter/kernels/gophernotes
RUN cd ~/.local/share/jupyter/kernels/gophernotes
RUN cp "$(go env GOPATH)"/pkg/mod/github.com/gopherdata/gophernotes@v0.7.5/kernel/*  "."
RUN chmod +w ./kernel.json
RUN sed "s|gophernotes|$(go env GOPATH)/bin/gophernotes|" < kernel.json.in > kernel.json


COPY bootstrap.sh /home/bootstrap.sh
EXPOSE 8000
EXPOSE 8001
ENTRYPOINT ["/bin/bash", "/home/bootstrap.sh"]




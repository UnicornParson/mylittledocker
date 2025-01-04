FROM jupyter/datascience-notebook:latest
#  docker run -p 8888:8888 jupyter/base-notebook:latest start-notebook.sh --NotebookApp.token=''
USER root
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && apt upgrade -y
RUN apt-get update && apt install -y linux-libc-dev software-properties-common
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
git \
python3-psycopg2 \
pandoc texlive-xetex \
texlive-fonts-recommended \
texlive-plain-generic \
ffmpeg \
p7zip \
golang
RUN apt-get update && apt install -y tesseract-ocr
USER jovyan
COPY .condarc /home/jovyan/.condarc

RUN conda update conda
RUN conda install -y -c conda-forge -c anaconda numpy tqdm pandas pympler numba tensorflow 
# no reprint in conda
# no videohash ImageHash xmltodict
RUN conda install -y -c conda-forge -c anaconda pytesseract matplotlib matplotlib-inline line_profiler youtube-dl
RUN conda install -y -c conda-forge -c anaconda pymongo line_profiler nbconvert pyppeteer 
RUN conda install -c pytorch torchvision torchaudio cpuonly cudatoolkit python-dotenv
RUN conda install opencv
RUN conda install scikit-learn seaborn pyvis


FROM jupyter/datascience-notebook:latest

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
golang \
tesseract-ocr

USER jovyan
COPY .condarc /home/jovyan/.condarc

RUN conda update conda 
RUN conda install -y pip
RUN conda install -y numpy tqdm pandas pympler numba tensorflow 
# no reprint in conda
# no videohash ImageHash xmltodict
RUN conda install -y pytesseract matplotlib matplotlib-inline line_profiler youtube-dl
RUN conda install -y pymongo line_profiler nbconvert pyppeteer python-dotenv
RUN conda install -y torchvision torchaudio cpuonly cudatoolkit  pytorch torchaudio 
RUN conda install -y opencv tesseract keras scipy xgboost
RUN conda install -y scikit-learn seaborn pyvis psycopg2 redis redis-py
RUN conda install -y gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav

RUN pushd /opt/conda/ && \
source activate && \
conda activate && \
pip install jycm ImageHash xmltodict reprint tabulate imageio[ffmpeg] jsonpickle humanize  && \
pip install git+https://github.com/faustomorales/keras-ocr.git#egg=keras-ocr && \
popd
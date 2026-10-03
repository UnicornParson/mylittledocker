# syntax=docker/dockerfile:1

# ============================================================
# Universal JupyterLab workstation
#
# Python       3.13
# CUDA toolkit 12.8
# PyTorch      2.11 + CUDA 12.8
# TensorFlow   GPU
# NeMo         2.7.x
#
# Scientific Python
# Computer Vision
# Video / Audio
# OCR
# C++ / CUDA development
# C++ Jupyter kernel
#
# NO R
# NO Julia
# ============================================================


# ------------------------------------------------------------
# Base
#
# scipy-notebook gives us:
#   - JupyterLab
#   - Python 3.13
#   - NumPy
#   - SciPy
#   - Pandas
#   - scikit-learn
#   - Matplotlib
#   - many standard scientific packages
#
# The Python version is deliberately NOT "latest".
# ------------------------------------------------------------

FROM quay.io/jupyter/scipy-notebook:python-3.13.14


# ------------------------------------------------------------
# Build arguments
#
# These are intentionally optional.
#
# Direct connection:
#
#   docker build -t my-jupyter .
#
# With HTTP/HTTPS proxy:
#
#   docker build \
#       --build-arg HTTP_PROXY=http://proxy:3128 \
#       --build-arg HTTPS_PROXY=http://proxy:3128 \
#       -t my-jupyter .
#
# SOCKS5:
#
#   docker build \
#       --build-arg ALL_PROXY=socks5h://user:password@host:1080 \
#       -t my-jupyter .
#
# Do NOT put credentials directly into .condarc.
# ------------------------------------------------------------

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG FTP_PROXY
ARG ALL_PROXY
ARG NO_PROXY


# ------------------------------------------------------------
# Runtime environment
# ------------------------------------------------------------

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:${PATH} \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility


USER root


# ============================================================
# Basic system packages
# ============================================================

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    gnupg \
    software-properties-common \
    apt-transport-https \
    nano \
    vim \
    htop \
    tree \
    less \
    jq \
    openssh-server \
    net-tools \
    iproute2 \
    iputils-ping \
    dnsutils \
    procps \
    lsof \
    psmisc \
    unzip \
    zip \
    p7zip-full \
    git \
    git-lfs \
    perl \
    gcc \
    g++ \
    make \
    build-essential \
    cmake \
    ninja-build \
    pkg-config \
    gdb \
    clang \
    clangd \
    clang-format \
    lldb \
    libcap-dev \
    libxml2-dev \
    libssl-dev \
    zlib1g-dev \
    libffi-dev \
    python3-dev \
    python3-psycopg2 \
    pandoc \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-plain-generic \
    ffmpeg \
    golang \
    tesseract-ocr \
    tesseract-ocr-eng \
    libsndfile1 \
    && \
    git lfs install --system \
    && \
    rm -rf /var/lib/apt/lists/*


# ============================================================
# CUDA 12.8 repository
#
# NVIDIA DRIVER IS NOT INSTALLED HERE.
#
# The host provides:
#
#   NVIDIA driver
#   NVIDIA Container Toolkit
#
# The container provides:
#
#   CUDA user-space toolkit
#   nvcc
#   headers
#   development libraries
# ============================================================

RUN wget -qO /tmp/cuda-keyring.deb \
    https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb \
    && \
    dpkg -i /tmp/cuda-keyring.deb \
    && \
    rm -f /tmp/cuda-keyring.deb \
    && \
    apt-get update \
    && \
    apt-get install -y --no-install-recommends \
    cuda-toolkit-12-8 \
    && \
    rm -rf /var/lib/apt/lists/*


# ============================================================
# CUDA compiler verification
# ============================================================

RUN nvcc --version


# ============================================================
# Conda configuration
#
# R and Julia are deliberately absent.
#
# We use Conda only for packages where Conda is useful.
# Heavy ML packages are installed through pip.
# ============================================================

USER jovyan

COPY --chown=jovyan:users .condarc /home/jovyan/.condarc


# ============================================================
# Make sure the base Python is really 3.13
# ============================================================

RUN python --version && \
    python -c "import sys; assert sys.version_info >= (3,13); print(sys.version)"


# ============================================================
# Update pip tooling
# ============================================================

RUN python -m pip install --upgrade \
    pip \
    setuptools \
    wheel \
    packaging


# ============================================================
# Additional scientific / utility packages
#
# Most of the basic scientific stack already comes from
# scipy-notebook.
#
# These are the packages from your original Dockerfile that
# are not guaranteed to be present there.
# ============================================================

RUN python -m pip install \
    tqdm \
    pympler \
    line_profiler \
    pymongo \
    pyvis \
    psycopg2-binary \
    redis \
    pytesseract \
    python-dotenv \
    pyppeteer \
    nbconvert \
    jycm \
    ImageHash \
    xmltodict \
    reprint \
    tabulate \
    imageio[ffmpeg] \
    jsonpickle \
    humanize


# ============================================================
# Computer Vision
#
# We deliberately use pip OpenCV here rather than adding a
# second OpenCV stack through Conda.
# ============================================================

RUN python -m pip install opencv-python-headless

# ============================================================
# PyTorch
#
# Official CUDA 12.8 wheels.
#
# PyTorch 2.11
# torchvision 0.26
# torchaudio 2.11
# ============================================================

RUN python -m pip install \
    torch==2.11.0 \
    torchvision==0.26.0 \
    torchaudio==2.11.0 \
    --index-url https://download.pytorch.org/whl/cu128


# ============================================================
# TensorFlow
#
# GPU dependencies are installed through TensorFlow's
# official "and-cuda" extra.
#
# This avoids trying to make Conda solve TensorFlow + CUDA.
# ============================================================

RUN python -m pip install \
    "tensorflow[and-cuda]"


# ============================================================
# OCR
# ============================================================

RUN python -m pip install \
    keras-ocr


# ============================================================
# XGBoost
#
# Python package. CUDA support is available when using the
# appropriate XGBoost build/configuration.
# ============================================================

RUN python -m pip install \
    xgboost


# ============================================================
# C++ Python integration
# ============================================================

RUN python -m pip install \
    pybind11 \
    cppimport


# ============================================================
# NVIDIA NeMo
#
# Current NeMo Toolkit requires Python >= 3.12 and PyTorch
# >= 2.6, so Python 3.13 + PyTorch 2.11 satisfies the stated
# package requirements.
#
# We keep this in a separate layer because it has a large
# dependency tree.
# ============================================================

RUN python -m pip install \
    Cython \
    packaging

RUN python -m pip install \
    "nemo_toolkit[all]"


# ============================================================
# C++ Jupyter kernel
#
# xeus-cling is installed through conda-forge.
#
# This gives Jupyter kernels such as:
#
#   C++11
#   C++14
#   C++17
#   C++20
#
# depending on the installed xeus-cling build.
# ============================================================

RUN mamba install -y \
    -c conda-forge \
    xeus-cling \
    && \
    mamba clean -afy


# ============================================================
# JupyterLab extensions / utilities
# ============================================================

RUN python -m pip install \
    jupyterlab-git


# ============================================================
# Environment diagnostics
# ============================================================
# ============================================================
# Environment diagnostics
# ============================================================

RUN python -c "\
    import sys; \
    print('=' * 70); \
    print('PYTHON'); \
    print('=' * 70); \
    print(sys.version); \
    assert sys.version_info >= (3, 13); \
    \
    import jupyterlab; \
    print('JupyterLab:', jupyterlab.__version__); \
    \
    import numpy; \
    print('NumPy:', numpy.__version__); \
    \
    import pandas; \
    print('Pandas:', pandas.__version__); \
    \
    import scipy; \
    print('SciPy:', scipy.__version__); \
    \
    import sklearn; \
    print('scikit-learn:', sklearn.__version__); \
    \
    import cv2; \
    print('OpenCV:', cv2.__version__); \
    \
    import torch; \
    print('PyTorch:', torch.__version__); \
    print('PyTorch CUDA:', torch.version.cuda); \
    print('CUDA available:', torch.cuda.is_available()); \
    \
    import tensorflow as tf; \
    print('TensorFlow:', tf.__version__); \
    print('TensorFlow GPUs:', tf.config.list_physical_devices('GPU')); \
    \
    import os; \
    print('CUDA_HOME:', os.environ.get('CUDA_HOME')); \
    \
    print('=' * 70); \
    print('DONE'); \
    print('=' * 70)"
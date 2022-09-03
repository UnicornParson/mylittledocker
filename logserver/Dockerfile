FROM python:latest
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && apt upgrade -y && apt install -y htop
RUN pip install --upgrade pip
RUN pip install flask psycopg2 beautifulsoup4

COPY bootstrap.sh /home/bootstrap.sh
COPY logserver.py /home/logserver.py
ENTRYPOINT [ "/bin/bash", "/home/bootstrap.sh"]

EXPOSE 1514
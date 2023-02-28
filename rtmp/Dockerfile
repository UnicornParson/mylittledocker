FROM ubuntu:latest
## use
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt upgrade -y && apt install -y \
ca-certificates \
gnupg1 \
lsb-release \
nginx-full \
libnginx-mod-rtmp \
ffmpeg

RUN rm -vf /etc/nginx/nginx.conf /etc/nginx/conf.d/default.conf
RUN mkdir -p /var/log/nginx/log && chown www-data:www-data /var/log/nginx/log
VOLUME /usr/share/nginx/html/hlslive
VOLUME /var/log/nginx/log

COPY ./nginx.conf /etc/nginx/nginx.conf
COPY ./entrypoint.sh /home/entrypoint.sh
COPY ./media/190301_1_25_11.mp4 /home/example.mp4
EXPOSE 1935
EXPOSE 5050
#CMD ["nginx", "-g", "daemon off;"]
CMD ["/bin/bash", "-c", "/home/entrypoint.sh"]
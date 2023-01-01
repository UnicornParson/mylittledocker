FROM ubuntu:latest
## use
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt upgrade -y && apt install -y \
ca-certificates \
gnupg1 \
lsb-release \
nginx-full \
libnginx-mod-rtmp

RUN rm -vf /etc/nginx/nginx.conf /etc/nginx/conf.d/default.conf
VOLUME /usr/share/nginx/html/hlslive
COPY ./nginx.conf /etc/nginx/nginx.conf
EXPOSE 1935
EXPOSE 5050
CMD ["nginx", "-g", "daemon off;"]
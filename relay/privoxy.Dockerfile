FROM alpine:latest
USER root
RUN apk --no-cache add privoxy bash
ADD cfg/privoxy-start.sh /usr/local/bin/privoxy-start.sh
ADD cfg/privoxy_minimal.config /etc/privoxy/config
SHELL ["/bin/bash", "-c"]
RUN cat /etc/privoxy/config
RUN chmod a+r /etc/privoxy/config 
RUN chmod a+x /usr/local/bin/privoxy-start.sh

CMD ["privoxy-start.sh"]

EXPOSE 9051
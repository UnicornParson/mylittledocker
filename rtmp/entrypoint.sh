#!/bin/bash

#nginx -g daemon off;

ffmpeg -re -stream_loop -1 -i /home/example.mp4 \
-vf drawtext="fontfile=monofonto.ttf: fontsize=96: box=1: boxcolor=black@0.75: boxborderw=5: fontcolor=white: x=(w-text_w)/2: y=((h-text_h)/2)+((h-text_h)/4): text='%{gmtime\:%H\\\\\:%M\\\\\:%S}'" \
-c:v libx264 -c:a aac -f flv -r 60 \
rtmp://127.0.0.1/hlslive/example &

exec nginx -g 'daemon off;' "$@"
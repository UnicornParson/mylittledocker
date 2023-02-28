# Ports

- 1935 - rtmp port. url example: rtmp://{host}/hlslive/{streamName}
- 5050 - {host}:5050/hlslive/{channel}.m3u8

# streams
## example
{host}:5050/hlslive/example.m3u8
source: 190301_1_25_11.mp4

**Stock footage provided by Stand Up For Nature, downloaded from videvo.net**

## how to make a stream
`ffmpeg -re -stream_loop -1 -i ts/example.ts -vf drawtext="fontfile=monofonto.ttf: fontsize=96: box=1: boxcolor=black@0.75: boxborderw=5: fontcolor=white: x=(w-text_w)/2: y=((h-text_h)/2)+((h-text_h)/4): text='%{gmtime\:%H\\\\\:%M\\\\\:%S}'" -c:v libx264 -c:a aac -f flv -r 60 rtmp://192.168.0.18/hlslive/example`
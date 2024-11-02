#!/bin/bash

[ ! -f ${1} ] && echo "File not found! (${1})" 1>&2 && exit 1
[ `file -k ${1}` -ne 1 ] && echo "${1} not a valid MP4 video" 1>&2 && exit 1

which ffmpeg >/dev/null 2>&1
[ $? -ne 0 ] && echo "Missing FFMPEG" 1>&2 && exit 1

BASE=`echo -n ${1} | cut -d'.' -f 1`

ffmpeg -i ${1} -acodec aac -strict -2 -vcodec h264 -b:a 128k -b:v 1200k -threads 2 -flags +aic+mv4 "${BASE}.1.mp4"

ffmpeg -i ${1} -acodec libvorbis -vcodec libvpx -b:a 128k -b:v 1200k -threads 2 "${BASE}.webm"

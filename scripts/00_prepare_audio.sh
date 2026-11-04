#!/bin/bash
# run inside $KIT_WORK/n1 (where src.mp4 is): extract the two audio files the next steps need
ffmpeg -v error -y -i src.mp4 -vn -ac 1 -ar 16000 a16.wav
ffmpeg -v error -y -i src.mp4 -vn -ac 1 -ar 44100 a44.wav

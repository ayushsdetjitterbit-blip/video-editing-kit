#!/bin/bash
# join the 300-frame chunks into presenter2.mp4, then 07_relight.py makes presenter3.mp4 (the file the project uses as assets/presenter.mp4)
ls "$PWD"/chunks2/p_*.mp4 | sed "s#^#file '#; s#\$#'#" > list2.txt
ffmpeg -v error -y -f concat -safe 0 -i list2.txt -c copy -movflags +faststart presenter2.mp4

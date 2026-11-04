#!/bin/bash
# replace one time window of the finished video with a separately rendered segment (see 12_still_segment.py), without re-rendering everything
# usage: 13_splice_segment.sh final_HQ.mp4 seg_still.mp4 80.15 83.90 out_HQ.mp4
IN=$1; SEG=$2; T0=$3; T1=$4; OUT=$5
D=$(python3 -c "print(round($T1-$T0,3))")
ffmpeg -v error -y -i "$IN" -i "$SEG" -filter_complex "[1:v]trim=duration=$D,setpts=PTS-STARTPTS+$T0/TB[s];[0:v][s]overlay=eof_action=pass:enable='between(t,$T0,$T1)'[v]" \
  -map "[v]" -map 0:a -c:v libx264 -crf 12 -preset medium -pix_fmt yuv420p -c:a copy -movflags +faststart "$OUT"
# small share copy:
ffmpeg -v error -y -i "$OUT" -c:v libx264 -crf 20 -preset medium -c:a copy -movflags +faststart "${OUT%.mp4}_share.mp4"

#!/bin/bash
# run from $KIT_WORK/n1 :  bash <kit>/scripts/06_run_chunks.sh [first_chunk_start] [last_chunk_start]
# face restoration in 300-frame chunks; a finished chunk leaves chunks2/p_NNNNN.mp4.done so a restart skips it. ONE worker at a time (each loads the whole clip, ~6 GB).
K="$(cd "$(dirname "$0")" && pwd)"; mkdir -p chunks2
FIRST=${1:-0}; LAST=${2:-2400}
for s in $(seq $FIRST 300 $LAST); do
  e=$((s+300)); N=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 clean_dn.mp4); [ $e -gt $N ] && e=$N
  f=$(printf "chunks2/p_%05d.mp4" $s)
  [ -s "$f.done" ] && continue
  python3 -I "$K/06_presenter_chunk.py" $s $e >> chunks2.log 2>&1 && touch "$f.done"
done
echo ALLDONE >> chunks2.log

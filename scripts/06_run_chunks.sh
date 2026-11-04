#!/bin/bash
cd "$(dirname "$0")"
for s in $(seq 0 300 2678); do
  e=$((s+300)); [ $e -gt 2679 ] && e=2679
  f=$(printf "chunks2/p_%05d.mp4" $s)
  if [ -s "$f.done" ]; then continue; fi
  python3 -I presenter_chunk2.py $s $e >> chunks2.log 2>&1 && touch "$f.done"
done
echo ALLDONE >> chunks2.log

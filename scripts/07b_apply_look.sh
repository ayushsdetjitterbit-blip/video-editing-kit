#!/bin/bash
# "P1" look, chosen for the final video: protects highlights (white coat and wall no longer glow), natural colour, light sharpening.
# Run inside $KIT_WORK/n1 after 07_relight.py:  presenter3.mp4 -> presenter4.mp4 (copy that to $KIT_PROJECT/assets/presenter.mp4).
# Do NOT also add a CSS brightness/contrast filter on the presenter in the HyperFrames root (older versions did; it made the picture too bright).
ffmpeg -v error -y -i presenter3.mp4 \
  -vf "curves=all='0/0.01 0.3/0.29 0.5/0.47 0.7/0.64 0.85/0.77 1/0.90',eq=saturation=1.04,unsharp=5:5:0.4:5:5:0.0" \
  -c:v libx264 -crf 12 -preset medium -pix_fmt yuv420p -g 30 -movflags +faststart presenter4.mp4

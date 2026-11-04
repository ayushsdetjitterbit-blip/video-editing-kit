#!/bin/bash
# B-roll used in the latest video (Mixkit Free License). 720p versions; copy into the HyperFrames project's assets/ folder.
D="${KIT_PROJECT:-./project}/assets"; mkdir -p "$D"; cd "$D"
for id in 33383 24658 6061; do curl -L -o "m$id.mp4" "https://assets.mixkit.co/videos/$id/$id-720.mp4"; done
# 33383 young woman with premenstrual pain | 24658 woman with a stomach ache | 6061 ultrasound machine in use
# br_herbal_oil.mp4 = Mixkit #33000 (plant-oil preparation), trimmed to 1008x566:
curl -L -o br_herbal_oil_full.mp4 "https://assets.mixkit.co/videos/33000/33000-720.mp4"
ffmpeg -y -i br_herbal_oil_full.mp4 -vf "scale=1008:566:force_original_aspect_ratio=increase,crop=1008:566" -an br_herbal_oil.mp4
# Fonts: put Noto Sans Devanagari (weight 800, woff2) at assets/fonts/NotoSansDevanagari-800.woff2 (Google Fonts, SIL OFL).

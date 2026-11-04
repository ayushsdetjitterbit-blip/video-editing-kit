#!/bin/bash
# assemble the HyperFrames generator from its four parts and run it (writes index.html + compositions/ into $KIT_PROJECT)
set -e
cd "$(dirname "$0")/../hyperframes_generator"
cat part1_head.py part2_scenes_and_captions.py part3_caption_template.py part4_root_and_ui.py > /tmp/gen_video.py
mkdir -p "${KIT_PROJECT:-./project}/compositions" "${KIT_WORK:-.}/v9"
python3 -I /tmp/gen_video.py

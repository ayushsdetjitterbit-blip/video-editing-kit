#!/bin/bash
# final render (PNG frames, CRF 14). Needs ~6 GB free disk for the extracted frames; delete /tmp/hyperframes-extract-cache-0 after a failed render.
cd "${KIT_PROJECT:-./project}"
npx hyperframes render --quality delivery --crf 14 --video-frame-format png -o "${1:-final_HQ.mp4}"

#!/bin/bash
# light temporal+spatial denoise of the clean cut before face restoration (removes WhatsApp block noise)
ffmpeg -v error -y -i clean_master.mp4 -vf "hqdn3d=2.5:2.0:5:4" -c:v libx264 -crf 10 -preset veryfast -an clean_dn.mp4

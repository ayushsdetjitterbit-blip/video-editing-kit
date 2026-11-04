#!/bin/bash
# face restoration + matting models (ONNX), from Hugging Face. ~1 GB total. Put them in $KIT_WORK/v8/models
set -e
D="${KIT_WORK:-.}/v8/models"; mkdir -p "$D"; cd "$D"
curl -L -o gpen_bfr_512.onnx https://huggingface.co/facefusion/models-3.0.0/resolve/main/gpen_bfr_512.onnx   # used for the face (GPEN, version "E")
curl -L -o gfpgan_1.4.onnx   https://huggingface.co/facefusion/models-3.0.0/resolve/main/gfpgan_1.4.onnx     # tested, not used in the final
curl -L -o codeformer.onnx   https://huggingface.co/facefusion/models-3.0.0/resolve/main/codeformer.onnx     # tested, not used in the final
curl -L -o modnet.onnx       https://huggingface.co/Xenova/modnet/resolve/main/onnx/model.onnx               # portrait matting (loaded by 06_presenter_chunk.py; output not used in the final)

# Credits and licences

- **HyperFrames** (HTML -> video renderer, by HeyGen) and **GSAP 3.14.2**: used as installed via npm (`npx hyperframes`).
- **faster-whisper** (large-v3) for transcription; **ffmpeg** for all cutting, encoding and splicing.
- **GPEN BFR 512** (face restoration), **MODNet** (portrait matting), **GFPGAN 1.4** and **CodeFormer** (tested): ONNX builds from Hugging Face (`facefusion/models-3.0.0`, `Xenova/modnet`). Check each model's licence before commercial use.
- **Real-ESRGAN general-x4v3** (neural upscaling) was tested in early versions only.
- **Music:** "Raising Me Higher", Ahjay Stelino. Mixkit Stock Music Free License.
- **B-roll:** Mixkit Free License - #33383, #24658, #6061, #33000 (and earlier versions: #4582, #17412, #6580, #4773, #32058, #48385, #4554, #4863, #6110).
- **Fonts:** Inter and Noto Sans Devanagari (SIL Open Font License).
- **Sound effects:** synthesised in `scripts/audio_helpers.py`.
- Rules in `docs/EDITING_RULES.md` borrow ideas from Nate Herk's `herk-edit-kit` (read and summarised, no code copied).

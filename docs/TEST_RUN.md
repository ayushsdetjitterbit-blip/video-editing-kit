# Test run (2026-11-04)

Ran the kit from a fresh work folder on the original 94 s recording and compared with the files used for the delivered video.

| Step | Result |
|---|---|
| 0 downloads | music, B-roll (4 clips + herbal oil), models (HTTP 200) and the Devanagari font work |
| 1-2 pauses + transcription | ran; 18 phrase windows |
| 3 cut | **timeline.json identical** to the one used (18 segments, 89.27 s, 2679 frames) after adding `LAST_END = 93.78` |
| 4-5 voice | `voice_enh.wav` **byte-identical** |
| 6 face chunk 0 (300 frames) | ran in 347 s; PSNR 45.7 dB vs the original chunk (encoder noise only) |
| 7 join + relight | ran; PSNR 44 dB vs the delivered `presenter3.mp4` on the same frames |
| 8 generator | `schedule.json` (events, groups) **identical**; `hyperframes check`: 0 errors, same 5 warnings as before |
| 9 audio | same loudness (-12.8 LUFS before the limiter); sample difference is 35.6 dB below the mix (random noise seeds in the SFX) |
| 11-12 still segment | rendered the 3.75 s segment and spliced it into the previous version: PSNR 40-49 dB vs the delivered file |
| Not repeated | the full 89 s final render (15-20 min) and the full face pass (2679 frames, ~45 min) |

## Breaks found and fixed
1. `06_run_chunks.sh` pointed to a renamed script and a wrong folder -> rewritten (run it from `n1/`).
2. OpenCV 5.x wheels have no face cascade -> the script downloads it, `requirements.txt` pins opencv 4.x.
3. Cut script missed the 0.04 s tail of the last word -> `LAST_END`.
4. Video length was hard-coded (89.27 s) -> computed from `timeline.json`.
5. The segment script needed manual project setup -> it now creates it.
6. Added `00_prepare_audio.sh`, `00_download_fonts.sh`, project scaffold instructions.
7. `07_relight.py` ends with a harmless "Broken pipe" message from ffmpeg when one input ends first.

# video-editing-kit

The code used to edit the "Period pain / Dysmenorrhea" talking-head video (Hinglish, 1080x1920, 89 s): transcribe, cut silences, restore the face, clean the voice, build Apple-style graphics with **HyperFrames**, mix music and sound effects, render, and patch single segments without re-rendering.

> **Status (please read):** the scripts here are the ones that produced the video. Afterwards the hard-coded paths were replaced with environment variables (`KIT_WORK`, `KIT_PROJECT`) so they can live in a repo. That path change, and the new `01`/`03`/`04` helper files (rewritten from commands I ran inline), have **not been re-run end to end**. Expect to fix a path or two on the first run. Videos, models and music are not stored in git (see `.gitignore`); the download scripts fetch them.

## What you need
- Python 3.11+, `pip install -r requirements.txt`
- ffmpeg + ffprobe on PATH, Node 22+ (HyperFrames runs through `npx hyperframes`), Chrome/Chromium
- A 4-core machine with ~16 GB RAM and ~15 GB free disk. The face pass takes about 1 s/frame; the final render about 15 minutes.

## Folder layout
```
$KIT_WORK/                  work folder (default: current directory)
  n1/                       per-video stage: src.mp4, a16.wav, a44.wav, tr2.json, timeline.json, clean_master.mp4, audio/ ...
  v8/models/                ONNX models (00_download_models.sh)
  v3/music/34.mp3           music bed (00_download_music.sh)
  v9/schedule.json          written by the HyperFrames generator, read by the audio and still-segment scripts
$KIT_PROJECT/               HyperFrames project (index.html, compositions/, assets/) - default $KIT_WORK/project
```
Run the `n1` scripts from `$KIT_WORK/n1`.

## Run order
| # | Script | What it does |
|---|---|---|
| 0 | `00_download_models.sh`, `00_download_music.sh`, `00_download_broll.sh` | models, music, B-roll |
| 1 | `01_find_pauses.py` | speech runs and pauses from audio energy -> `runs.json` |
| 2 | `02_transcribe_windows.py` | transcribes each phrase window separately (large-v3 skips text in long windows) -> `tr2.json` |
| 3 | `03_build_cut.py` | cuts only between phrases, frame-exact -> `timeline.json`, `clean_master.mp4` |
| 4 | `04_build_voice.py` | voice rebuilt from the original audio at the same cuts |
| 5 | `05_enhance_voice.py` | noise reduction (noise profile from the pauses), light EQ, loudness; verifies pitch is unchanged |
| 6 | `06b_denoise_for_presenter.sh`, `06_run_chunks.sh` (+ `06_presenter_chunk.py`) | face restoration (GPEN) in 300-frame chunks that can be resumed |
| 7 | `08_join_presenter_chunks.sh`, `07_relight.py` | joins chunks, then keeps GPEN detail but takes lighting and skin tone from the real footage -> `presenter3.mp4` (copy to `$KIT_PROJECT/assets/presenter.mp4`) |
| 8 | `10_build_project.sh` | builds the HyperFrames project from `hyperframes_generator/` (graphics, B-roll scenes, captions) |
| 9 | `09_build_audio.py` | voice + ducked music + synthesised sound effects locked to the on-screen events -> `n1/audio/mix6.wav` -> `ffmpeg ... mix.m4a` into `assets/` |
| 10 | `11_render.sh` | final render |
| 11 | `12_still_segment.py` + `13_splice_segment.sh` | replace one time window (e.g. swap a clip for a still) by rendering only that window and overlaying it |

Content for a new video lives in `hyperframes_generator/part2_scenes_and_captions.py` (scene times, card text, caption chunks). Everything is anchored to source-time words through `M()` (source time -> cut timeline).

## Layout rules used
Presenter always full frame; cards sit below the chin (`top 1056 px`), captions at `top 1530 px`; full-screen B-roll for ~20 s in total; top 168 px kept clear. See `docs/EDITING_RULES.md` and `docs/LESSONS.md`.

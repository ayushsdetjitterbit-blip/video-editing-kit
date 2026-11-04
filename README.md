# video-editing-kit

The code used to edit the "Period pain / Dysmenorrhea" talking-head video (Hinglish, 1080x1920, 89 s): transcribe, cut silences, restore the face, clean the voice, build Apple-style graphics with **HyperFrames**, mix music and sound effects, render, and patch single segments without re-rendering.

> **Status:** the scripts were test-run on the original video (see `docs/TEST_RUN.md`). Steps 0-9 and the segment splice reproduced the delivered video's intermediate files; the full final render was not repeated. Videos, models and music are not stored in git (`.gitignore`); the download scripts fetch them.

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
| 0 | `00_download_models.sh`, `00_download_music.sh`, `00_download_broll.sh`, `00_download_fonts.sh`, `00_prepare_audio.sh` | models, music, B-roll, font, and the two wav files (run the last one inside `n1/`) |
| 1 | `01_find_pauses.py` | speech runs and pauses from audio energy -> `runs.json` |
| 2 | `02_transcribe_windows.py` | transcribes each phrase window separately (large-v3 skips text in long windows) -> `tr2.json` |
| 3 | `03_build_cut.py` | cuts only between phrases, frame-exact -> `timeline.json`, `clean_master.mp4` |
| 4 | `04_build_voice.py` | voice rebuilt from the original audio at the same cuts |
| 5 | `05_enhance_voice.py` | noise reduction (noise profile from the pauses), light EQ, loudness; verifies pitch is unchanged |
| 6 | `06b_denoise_for_presenter.sh`, `06_run_chunks.sh` (+ `06_presenter_chunk.py`) | face restoration (GPEN) in 300-frame chunks that can be resumed |
| 7 | `08_join_presenter_chunks.sh`, `07_relight.py` | joins chunks, then keeps GPEN detail but takes lighting and skin tone from the real footage -> `presenter3.mp4` (copy to `$KIT_PROJECT/assets/presenter.mp4`) |
| 7b | `07b_apply_look.sh` | the "P1" look (highlight protection, natural colour) -> `presenter4.mp4`, the file the project uses as `assets/presenter.mp4` |
| 8 | `npx hyperframes@0.8.225 init` once (see below), then `10_build_project.sh` | builds the HyperFrames project from `hyperframes_generator/` (graphics, B-roll scenes, captions) |
| 9 | `09_build_audio.py` | voice + ducked music + synthesised sound effects locked to the on-screen events -> `n1/audio/mix6.wav` -> `ffmpeg ... mix.m4a` into `assets/` |
| 10 | `11_render.sh` | final render |
| 11 | `12_still_segment.py` + `13_splice_segment.sh` | replace one time window (e.g. swap a clip for a still) by rendering only that window and overlaying it |

Content for a new video lives in `hyperframes_generator/part2_scenes_and_captions.py` (scene times, card text, caption chunks). Everything is anchored to source-time words through `M()` (source time -> cut timeline).

## Create the HyperFrames project once
```sh
cd $KIT_WORK && npx --yes hyperframes@0.8.225 init scaffold --example blank --resolution portrait --non-interactive --skip-skills
mkdir -p project/assets/fonts project/compositions
cp scaffold/{AGENTS.md,CLAUDE.md,hyperframes.json,meta.json,package.json} project/
```
Then run the `00_download_*` scripts, copy `n1/presenter4.mp4` to `project/assets/presenter.mp4`, copy `n1/audio/mix.m4a` (from `mix6.wav`, see below) into `project/assets/`, and run `10_build_project.sh` and `11_render.sh`. HyperFrames releases change often; the video was rendered with 0.8.222-0.8.225, so pin that version.

```sh
ffmpeg -i n1/audio/mix6.wav -af "volume=-1.0dB,alimiter=limit=0.89:level=disabled" -c:a aac -b:a 256k project/assets/mix.m4a
```

## Layout rules used
Presenter always full frame; cards sit below the chin (`top 1056 px`), captions at `top 1530 px`; full-screen B-roll for ~20 s in total; top 168 px kept clear. See `docs/EDITING_RULES.md` and `docs/LESSONS.md`.

# video-editing-kit (`vek`)

Turns a talking-head (or vlog) video into a finished, social-ready video: **clean cut, restored voice, natural iPhone-style look, captions, motion graphics, B-roll, music and sound effects, render, and automatic quality checks**. It is built to work on *any* video: every setting is measured from the video itself (size, frame rate, loudness, exposure, noise, faces), and the only thing that is specific to a video is its small **storyboard** file.

```sh
pip install -r requirements.txt
python -m vek doctor                      # checks ffmpeg, node, python packages
python -m vek init my_video.mp4 --name my_video --lang hi     # creates my_video/config.yaml + storyboard.yaml
python -m vek run my_video/config.yaml --stages ingest,transcribe,cut
python -m vek draft my_video/config.yaml  # transcript with timestamps -> write the storyboard
python -m vek run my_video/config.yaml    # everything (resumable: finished stages are skipped), ends with the QA report
```

## What is automatic (no per-video work)
| Stage | What it does | How it adapts |
|---|---|---|
| ingest | constant frame rate, rotation applied, 48 kHz audio | any fps (24/25/30/50/60), any size, phone rotation |
| transcribe | speech runs and phrase windows, Whisper per window, loop/hallucination guard | language `auto` or forced (`hi` for Hindi/Hinglish) |
| cut | cuts only between phrases; drops filler-only windows, repeated takes and false starts; frame- and sample-exact | thresholds in `config.yaml` (`cut:`), report of everything dropped |
| voice | rebuilt from the original audio at the cut, noise reduction from the recording's own pauses, EQ, de-ess, two-pass loudness | verification report (SNR, pitch change, LUFS) |
| picture | cover-scale to 1080x1920 (or 1920x1080), denoise, **face restoration only when it helps**, relight, **adaptive look** | measured brightness percentiles, face size, noise: dark videos are left alone, bright ones get highlight protection |
| captions | 1-4 word groups from real word timestamps | `captions.corrections` map, editable draft (`captions_draft.yaml`) |
| compose | HyperFrames project from the storyboard | graphics never cover a face (checked per beat) |
| mix | ducked music + soft synthesised SFX tied to the graphics | target loudness measured on the encoded file |
| render + qa | final video, then gates: size, duration, loudness, true peak, black frames, face visible, **no graphic or caption over the face** | `qa_report.json`; exit code 2 if a gate fails |

## What you write per video: `storyboard.yaml`
Beat types: `card`, `broll`, `still`, `checklist`, `tiles`, `term`, `follow`. Times are *source* seconds (before cuts) or `say:` words from the transcript.
See `docs/STORYBOARD.md` and `configs/example_storyboard.yaml`. B-roll files go in the video folder's `assets/`.

## Honest limits
- It can make a video look natural and clean; it **cannot add detail that the source does not have**. A 478x850 WhatsApp copy will always look softer than the original phone file. Use the original recording whenever you can.
- Face restoration (GPEN, CPU) takes about 1 s per frame; it runs in resumable chunks with bounded memory. It is only enabled when a face is found in most frames and the source is small. Its model is for non-commercial use; check licences (`CREDITS.md`).
- Landscape canvas supports captions, progress bar, `broll` and `still` beats only; the card/panel layout is designed for vertical video.
- Videos with few faces (vlogs) are detected as *scene videos*: cards move to the lower area and panels are refused unless you set `force: true`.
- The storyboard text and B-roll choice are content decisions and stay manual (or are written by an assistant from `vek draft`).
- Hindi/Hinglish transcripts need a quick read: Whisper mis-hears names and English words. Three ways to fix: `captions.corrections` (word map), edit `work/captions_draft.yaml` and save it as `work/captions_edited.yaml`, or write `captions_chunks.yaml` next to `config.yaml` (`- {t: <source seconds>, text: "..."}`) to replace the transcript-based captions completely.

## Layout
`vek/` the package, `tests/` unit tests (`python -m unittest discover -s tests`), `configs/` examples, `docs/`, `legacy/period-pain/` the original one-video scripts this kit was generalised from.

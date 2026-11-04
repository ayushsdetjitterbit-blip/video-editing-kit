# Test report (vek 1.0)

Unit tests: `python -m unittest discover -s tests` -> 17 tests (cut rules, loop guard, adaptive look, captions, storyboard and face-overlap logic).

End-to-end runs of the same code on three different videos (no per-video code, only a config and a storyboard):

| Video | Kind | What the kit decided by itself | Result |
|---|---|---|---|
| Period-pain explainer, 478x850, 94 s | talking head, bright white coat | 18 phrase windows, cut within 0.067 s of the hand-tuned cut (breath before one phrase trimmed automatically), voice SNR 29 -> 35 dB, pitch change 0.0% | stages ingest-voice run; full render was done earlier with the legacy scripts |
| NIA Jaipur day, 720x1280, 35 s | vlog / scene video (faces in 25% of frames), noisy audio | language had to be set to `hi` (auto said Urdu: a warning is printed), face restoration OFF, light look, cards moved to the lower area, panels refused unless `force: true` | full render, **QA passed** (loudness -14.1 LUFS, no black frames, no graphic over a face) |
| White-discharge clip, 478x850, 19 s | talking head, close framing, orange wall | face restoration ON (face in 100% of frames), denoise 0.77, look strength 0.65, panels auto-shrunk to stay below the chin, Whisper repetition loop detected and retried | full render, **QA passed** (-14.0 LUFS, -1.7 dBTP, face never covered) |

Bugs found by these runs and fixed: hard-coded 44.1 kHz and frame sizes, whole-clip decoding (memory), missing `<audio>` in the first render (QA caught "NO AUDIO"), `say:` anchors using the wrong clock, panels covering a close-up chin (now auto-shrunk or refused), false face detections on clothing, Whisper loops, urdu/hindi detection, loudness parsing.

Not covered by tests: landscape output (basic), videos longer than a few minutes (stages are resumable and chunked, but untested), non-Hindi/English languages, music (no licensed track is bundled; set `audio.music`).

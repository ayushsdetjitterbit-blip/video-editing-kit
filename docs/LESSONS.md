# Lessons from building this video

- **Source quality limits everything.** The WhatsApp copy is 478x850. Face restoration helps, but only the original phone file gives real iPhone sharpness.
- **Compare methods on 2 seconds first** (plain upscale, Real-ESRGAN, GFPGAN, CodeFormer, GPEN) before running a long job.
- **Face restoration changes how the person looks** (GFPGAN/CodeFormer removed a beauty mark). GPEN kept it. Always check identity.
- **Long jobs die.** Run them in resumable chunks (`06_run_chunks.sh`), never one big file with `+faststart` (a killed encoder leaves an unreadable file).
- **Memory:** each face-restoration worker loads the whole clip (~6 GB). Two workers in parallel on a 15 GB machine were killed. Run one at a time.
- **Disk:** a PNG-frame render needs ~5-6 GB; delete `/tmp/hyperframes-extract-cache-0` after a failed render. Failed with "no space" once.
- **`dict.setdefault(k, expensive())` evaluates `expensive()` every call** - this made one job 6x slower.
- **`np.convolve` for reverb on a 90 s signal takes ~20 min**; use `scipy.signal.fftconvolve`.
- **Whisper large-v3 drops text in windows longer than 30 s**: transcribe each phrase window separately.
- **Don't `pkill -f` a pattern that appears in your own command line** - it kills the shell. Match by PID.
- **Aurora/blur backgrounds and wall-dimming with a matte create halos and "noise"**: removed in favour of a plain background and a gentle highlight roll-off.
- Stock B-roll from Mixkit is 720p; stretched to 9:16 it is soft. Keep full-screen moments short.

## Vlog with a hesitant speaker (art gallery)
- Cutting **every** pause of a speaker who pauses a lot gives a jerky, laggy video (46 cuts, 8 in the first 10 s). `cut.pause_keep: 0.5` keeps natural pauses and only cuts where something was really removed (22 segments).
- Wobble comes from `vidstab` on wide-angle phone footage and from ghosting dissolves: intro clips now use hard cuts and no stabilisation by default.
- Whisper word times can be off by 0.3 s in noisy rooms: cut fillers by the energy curve, and verify by re-transcribing the cleaned audio (the prompt that makes Whisper write "uh" also makes it hallucinate "uh" at splices; judge by word probability).
- Cards over painting close-ups hide the content: use `chip` beats (small label at the top) or `on_conflict: chip`.
- A render can die at 95% when the disk fills with PNG frames (about 2 MB per frame): clean `/tmp/hyperframes-extract-cache-0`, vek now falls back to JPEG frames and retries.

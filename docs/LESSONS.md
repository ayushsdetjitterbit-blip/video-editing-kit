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

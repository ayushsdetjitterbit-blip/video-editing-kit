# Art gallery vlog (two videos -> one)

- Part 1 (silent 44 s phone clip): only 0:04-0:09, 0:13-0:19, 0:24-0:28 kept; each stabilised (ffmpeg `vidstab`), lightly denoised, graded with `vek.picture.look_params` (adaptive), 0.25 s dissolves between them.
  The clip has no audio (digital silence), so a quiet room-tone bed shaped from the speaker's own recording sits under it and crossfades into the voice.
- Part 2 (2:16 talking video): `config_speech_part.yaml`. Fillers (uh), stutters, false starts, repeated/abandoned sentences removed; no graphics, captions or images added.
  `drop_windows` and `excise` were chosen by reading `work/transcript.json`; because Whisper's word times were off by up to 0.3 s in this recording, each `uh` was cut using the energy curve.
- Join: 0.4 s dissolve (picture) and equal-power crossfade (sound), final loudness -14 LUFS.

"""Intro / montage clips that come BEFORE the talking part (e.g. a short walk through a gallery before the speaker starts).
config.yaml:
  intro:
    clips: [{file: gallery.mp4, start: 4, end: 9}, {file: gallery.mp4, start: 13, end: 19}]
    stabilize: false        # optional: ffmpeg vidstab (off by default: it can wobble wide-angle phone footage)
    dissolve: 0             # seconds of crossfade between clips; 0 = clean hard cuts (recommended)
The clips are trimmed frame-exactly, cover-scaled to the canvas, lightly denoised and given the same adaptive look as the main video. They carry no
sound of their own; the mix stage puts music and soft sound effects under them."""
import json, os, subprocess
import numpy as np
from .util import run, probe, log
from . import picture as P

def build(cfg, work, meta, base_dir):
    ic = cfg.get("intro") or {}; clips = ic.get("clips") or []
    if not clips: return 0.0
    fps = meta["fps"]; cw, ch = meta["canvas"]; parts = []; stats = []
    for k, c in enumerate(clips):
        f = c["file"] if os.path.isabs(c["file"]) else os.path.join(base_dir, c["file"])
        if not os.path.isfile(f): raise FileNotFoundError(f"intro clip not found: {f}")
        p = probe(f); s, e = float(c["start"]), float(c["end"])
        if not (0 <= s < e <= p["duration"] + 0.05): raise ValueError(f"intro clip {k}: start/end {s}-{e} outside the video ({p['duration']:.1f}s)")
        raw = os.path.join(work, f"intro_raw{k}.mp4"); sf = p["fps"]
        run(["ffmpeg", "-v", "error", "-y", "-i", f, "-vf", f"trim=start={s}:end={e},setpts=PTS-STARTPTS,fps={fps}", "-an", "-c:v", "libx264", "-crf", "8", "-preset", "veryfast", "-pix_fmt", "yuv420p", raw])
        if ic.get("stabilize"):
            trf = os.path.join(work, f"intro{k}.trf"); st = os.path.join(work, f"intro_stab{k}.mp4")
            run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-vf", f"vidstabdetect=shakiness=4:accuracy=12:result={trf}", "-f", "null", "-"])
            run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-vf", f"vidstabtransform=input={trf}:smoothing=12:optzoom=0:crop=black:interpol=bicubic", "-c:v", "libx264", "-crf", "8", "-preset", "veryfast", "-pix_fmt", "yuv420p", st]); raw = st
        raw_g = subprocess.run(["ffmpeg", "-v", "error", "-i", raw, "-vf", "fps=2,scale=232:-1", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
        stats.append(np.frombuffer(raw_g, np.uint8).astype(np.float32) / 255); parts.append(raw)
    L = np.concatenate(stats); st = dict(p50=float(np.percentile(L, 50)), p99=float(np.percentile(L, 99)), p1=float(np.percentile(L, 1)), width=probe(parts[0])["width"])
    lf = P.look_filter(P.look_params(st, cfg["picture"]["look"]))
    vf = f"hqdn3d=1.2:1.0:2.5:2.5,scale={cw}:{ch}:force_original_aspect_ratio=increase:flags=lanczos,crop={cw}:{ch}," + lf
    inputs = []; [inputs.extend(["-i", p_]) for p_ in parts]; n = len(parts); d = float(ic.get("dissolve", 0) or 0)
    if d > 0 and n > 1:
        durs = [probe(p_)["duration"] for p_ in parts]; fc = ""; cur = "[0:v]"; t = durs[0]
        for k in range(1, n):
            fc += f"{cur}[{k}:v]xfade=transition=fade:duration={d}:offset={t - d:.3f}[x{k}];"; cur = f"[x{k}]"; t = t - d + durs[k]
        fc += f"{cur}{vf}[v]"
    else: fc = "".join(f"[{k}:v]" for k in range(n)) + f"concat=n={n}:v=1:a=0[c];[c]{vf}[v]"
    out = os.path.join(work, "intro.mp4")
    run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-crf", "12", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(fps), "-an", out])
    dur = probe(out)["duration"]; cuts = []; t = 0.0
    for p_ in parts[:-1]: t += probe(p_)["duration"] - (d if d > 0 else 0); cuts.append(round(t, 3))
    json.dump(dict(duration=dur, cuts=cuts, look=st), open(os.path.join(work, "intro.json"), "w"))
    log(f"intro: {n} clips, {dur:.2f}s, cuts at {cuts}")
    return dur

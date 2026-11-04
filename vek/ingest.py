"""Stage 1: normalise the input so every later stage can count on the same facts.
Output: work/src.mp4 (constant frame rate, rotation applied), work/a16.wav (16 kHz mono, for speech analysis), work/a48.wav (48 kHz mono, the voice source).
48 kHz is used because 48000 / fps is a whole number of samples for 24, 25, 30, 50 and 60 fps, so cuts are sample-exact."""
import os
from .util import run, probe, log

FPS_CHOICES = (24, 25, 30, 50, 60)

def pick_fps(src_fps, cfg_fps):
    if cfg_fps != "auto": return int(cfg_fps)
    return min(FPS_CHOICES, key=lambda f: abs(f - src_fps))

def choose_canvas(w, h, canvas):
    if canvas == "vertical": return 1080, 1920
    if canvas == "landscape": return 1920, 1080
    return (1080, 1920) if h >= w else (1920, 1080)

def ingest(cfg, work):
    src = cfg["input"]; p = probe(src); os.makedirs(work, exist_ok=True)
    fps = pick_fps(p["fps"], cfg["fps"]); cw, ch = choose_canvas(p["width"], p["height"], cfg["canvas"])
    out = os.path.join(work, "src.mp4")
    vf = f"fps={fps}"          # ffmpeg autorotates by default; fps= makes variable-frame-rate phone video constant
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf, "-c:v", "libx264", "-crf", "10", "-preset", "veryfast", "-pix_fmt", "yuv420p"]
    cmd += (["-c:a", "aac", "-b:a", "256k", "-ar", "48000"] if p["has_audio"] else ["-an"]) + [out]
    log(f"ingest: {p['width']}x{p['height']} {p['fps']:.2f}fps {p['duration']:.1f}s -> cfr {fps} fps, canvas {cw}x{ch}")
    run(cmd)
    if not p["has_audio"]: raise ValueError("the input has no audio track; this kit edits spoken videos")
    run(["ffmpeg", "-v", "error", "-y", "-i", out, "-vn", "-ac", "1", "-ar", "16000", os.path.join(work, "a16.wav")])
    run(["ffmpeg", "-v", "error", "-y", "-i", out, "-vn", "-ac", "1", "-ar", "48000", os.path.join(work, "a48.wav")])
    q = probe(out)
    return dict(fps=fps, canvas=[cw, ch], src_w=q["width"], src_h=q["height"], duration=q["duration"], src_fps=p["fps"])

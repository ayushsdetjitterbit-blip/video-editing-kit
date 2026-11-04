"""Per-video configuration. Everything has a safe default; a config file only states what differs for this video."""
import os, yaml
from .util import deep_merge

DEFAULTS = {
    "input": None,                       # path to the source video
    "workdir": "work",                   # all intermediate files live here (resumable)
    "language": "auto",                  # whisper language code, or "auto"
    "canvas": "auto",                    # auto | vertical (1080x1920) | landscape (1920x1080)
    "fps": "auto",                       # auto = nearest of 24/25/30/50/60
    "cut": {
        "pause_min": 0.25,               # pauses shorter than this stay (natural beats)
        "pad_before": 0.07, "pad_after": 0.10,
        "drop_fillers": True,            # drop a window that is ONLY a filler (um, uh, ...), never cut inside a sentence
        "trim_breath": True,            # trim a breath / mouth noise (>= 0.25 s) before the first word of a phrase
        "drop_repeats": True,            # keep the best of repeated / restarted sentences
        "repeat_similarity": 0.82,
        "tail_pad": 0.10,                # extra time kept after the last word
        "start_overrides": {}, "end_overrides": {}, "drop_windows": [],   # manual fixes by window index
    },
    "voice": {"enhance": True, "target_lufs": -16, "noise_reduce": 0.85},
    "picture": {
        "denoise": "auto",               # auto | off | 0..1
        "face_restore": "auto",          # auto (only if a face is found and the source is small) | gpen | off
        "face_strength": 0.85,
        "relight": True,                 # keep restored detail, take lighting/skin tone from the real footage
        "look": "natural",               # natural | punchy | off   (adaptive: measured from the video itself)
    },
    "captions": {"enabled": True, "max_words": 4, "max_chars": 26, "corrections": {}, "style": "pill"},
    "graphics": {"storyboard": None, "progress_bar": True, "background": "#B4AFA5", "accent": "#0A84FF"},
    "audio": {"music": None, "music_level_db": -9.5, "sfx": True, "target_lufs": -14},   # music_level_db: relative to the voice level, before ducking
    "render": {"quality": "delivery", "crf": 14, "hyperframes_version": "0.8.225"},
}

def load(path):
    cfg = yaml.safe_load(open(path)) or {}
    cfg = deep_merge(DEFAULTS, cfg)
    base = os.path.dirname(os.path.abspath(path))
    for k in ("input", "workdir"):
        if cfg.get(k) and not os.path.isabs(cfg[k]): cfg[k] = os.path.normpath(os.path.join(base, cfg[k]))
    sb = cfg["graphics"].get("storyboard")
    if sb and not os.path.isabs(sb): cfg["graphics"]["storyboard"] = os.path.normpath(os.path.join(base, sb))
    m = cfg["audio"].get("music")
    if m and not os.path.isabs(m): cfg["audio"]["music"] = os.path.normpath(os.path.join(base, m))
    if not cfg["input"] or not os.path.isfile(cfg["input"]): raise FileNotFoundError(f"input video not found: {cfg['input']}")
    return cfg

"""Small helpers shared by all stages: running tools, reading probes, resumable stage state."""
import json, os, subprocess, shutil, hashlib, time, sys

def run(cmd, **kw):
    """Run a command, raise with the tail of stderr on failure (never hides errors)."""
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(map(str, cmd))[:300]}\n{(p.stderr or '')[-1500:]}")
    return p

def which(name): return shutil.which(name)

def probe(path):
    """ffprobe summary: size after rotation, fps (rational + rounded), duration, frames, audio."""
    p = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    j = json.loads(p.stdout); v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if v is None: raise ValueError("no video stream in " + path)
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd: rot = int(round(float(sd["rotation"]))) % 360
    if "rotate" in (v.get("tags") or {}): rot = int(v["tags"]["rotate"]) % 360
    if rot in (90, 270): w, h = h, w
    num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den) if float(den) else 30.0
    dur = float(j["format"].get("duration") or v.get("duration") or 0)
    return dict(width=w, height=h, rotation=rot, fps=fps, duration=dur, has_audio=a is not None,
                audio_rate=int(a["sample_rate"]) if a else None, codec=v.get("codec_name"),
                nb_frames=int(v["nb_frames"]) if v.get("nb_frames", "").isdigit() else None)

class Stage:
    """Marks a stage as done (with a fingerprint of its inputs) so reruns skip finished work."""
    def __init__(self, workdir): self.dir = os.path.join(workdir, ".state"); os.makedirs(self.dir, exist_ok=True)
    def _p(self, name): return os.path.join(self.dir, name + ".json")
    def done(self, name, fingerprint=""):
        try: return json.load(open(self._p(name))).get("fp") == fingerprint
        except Exception: return False
    def mark(self, name, fingerprint="", info=None): json.dump(dict(fp=fingerprint, t=time.time(), info=info or {}), open(self._p(name), "w"))
    def clear(self, name):
        if os.path.exists(self._p(name)): os.remove(self._p(name))

def fp(*items):
    h = hashlib.sha1()
    for it in items:
        if isinstance(it, (dict, list)): h.update(json.dumps(it, sort_keys=True, default=str).encode())
        elif isinstance(it, str) and os.path.isfile(it): h.update(f"{it}:{os.path.getsize(it)}:{int(os.path.getmtime(it))}".encode())
        else: h.update(str(it).encode())
    return h.hexdigest()[:16]

def log(msg): print(f"[vek] {msg}", flush=True)

def deep_merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out

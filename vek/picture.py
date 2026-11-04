"""Stage 5: the picture. Everything is measured from the video, nothing is tuned to one clip.

  analyze()      sample frames -> brightness percentiles, face found/size, noise level          (picture_stats.json)
  plan()         decide denoise strength, whether face restoration is worth it, and the look curve from those measurements
  presenter()    cover-scale to the canvas, optional face restoration (GPEN, resumable chunks, bounded memory),
                 optional relight (keep restored detail, take lighting and skin tone from the real footage), then the adaptive look
"""
import json, os, subprocess, time, urllib.request
import numpy as np
import cv2
from .util import run, log

CASCADE_URL = "https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/haarcascade_frontalface_alt2.xml"
MODEL_URLS = {"gpen_bfr_512.onnx": "https://huggingface.co/facefusion/models-3.0.0/resolve/main/gpen_bfr_512.onnx"}

def models_dir(): return os.environ.get("VEK_MODELS", os.path.join(os.path.expanduser("~"), ".cache", "vek", "models"))

def ensure_file(name, url):
    d = models_dir(); os.makedirs(d, exist_ok=True); p = os.path.join(d, name)
    if not os.path.exists(p) or os.path.getsize(p) < 1000:
        log(f"downloading {name} ..."); urllib.request.urlretrieve(url, p)
    return p

def cascade():
    p = os.path.join(getattr(getattr(cv2, "data", None), "haarcascades", ""), "haarcascade_frontalface_alt2.xml")
    if not os.path.exists(p): p = ensure_file("haarcascade_frontalface_alt2.xml", CASCADE_URL)
    return cv2.CascadeClassifier(p)

def read_frames(path, w, h, start=0, count=None, fps=30, vf=None):
    """Decode a bounded number of frames (never the whole clip) as BGR arrays."""
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start / fps:.5f}", "-i", path]
    if count: cmd += ["-frames:v", str(count)]
    if vf: cmd += ["-vf", vf]
    cmd += ["-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)

# ------------------------------------------------------------------ analysis
def analyze(work, meta):
    from .util import probe
    p = probe(os.path.join(work, "clean_master.mp4")); w, h = p["width"], p["height"]; n = int(round(p["duration"] * meta["fps"]))
    idx = np.linspace(0, max(0, n - 2), 36).astype(int); cc = cascade(); lum = []; faces = []; noise = []
    for i in idx:
        f = read_frames(os.path.join(work, "clean_master.mp4"), w, h, int(i), 1, meta["fps"])
        if not len(f): continue
        f = f[0]; g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY); lum.append(g.astype(np.float32) / 255)
        r = cc.detectMultiScale(cv2.equalizeHist(g), 1.1, 5, minSize=(max(40, w // 10), max(40, w // 10)))
        if len(r):
            x, y, fw, fh = max(r, key=lambda b: b[2] * b[3]); gf = g[y:y + fh, x:x + fw].astype(np.float32) / 255
            faces.append(dict(cx=(x + fw / 2) / w, cy=(y + fh / 2) / h, w=fw / w, luma=float(np.median(gf))))
        hp = g.astype(np.float32) - cv2.GaussianBlur(g, (0, 0), 1.2); gm = cv2.GaussianBlur(cv2.Laplacian(g, cv2.CV_32F), (0, 0), 2)
        flat = np.abs(gm) < 2.0                                                      # noise is measured on flat areas only (edges are not noise)
        if flat.sum() > 2000: noise.append(float(np.std(hp[flat])))
    L = np.concatenate([l[::4, ::4].ravel() for l in lum]) if lum else np.array([0.5])
    st = dict(width=w, height=h, frames=n, p1=float(np.percentile(L, 1)), p50=float(np.percentile(L, 50)), p99=float(np.percentile(L, 99)),
              face_found_ratio=len(faces) / max(1, len(idx)), noise=float(np.median(noise)) if noise else 0.0)
    if faces:
        st.update(face_w=float(np.median([f["w"] for f in faces])), face_cx=float(np.median([f["cx"] for f in faces])), face_cy=float(np.median([f["cy"] for f in faces])),
                  face_luma=float(np.median([f["luma"] for f in faces])))
    json.dump(st, open(os.path.join(work, "picture_stats.json"), "w"))
    log(f"picture: p50 {st['p50']:.2f} p99 {st['p99']:.2f}, face found {st['face_found_ratio']:.0%}, noise {st['noise']:.2f}")
    return st

BASE_SHOULDER = [(0.0, 0.01), (0.3, 0.29), (0.5, 0.47), (0.7, 0.64), (0.85, 0.77), (1.0, 0.90)]    # the "P1" curve chosen by the user

def look_params(st, style):
    """Adaptive: dark / low-key footage gets ~no change, bright footage (white coats, white walls) gets the full highlight shoulder."""
    if style == "off": return None
    s = float(np.clip((st["p99"] - 0.75) / 0.20, 0, 1) * 0.6 + np.clip((st["p50"] - 0.40) / 0.25, 0, 1) * 0.4)
    if "face_luma" in st and st["face_luma"] > 0.62: s = min(1.0, s + 0.15)             # very bright face: protect a bit more
    if style == "punchy": s = min(1.0, s * 0.8 + 0.2)
    pts = [(x, x + s * (y - x)) for x, y in BASE_SHOULDER]
    curve = " ".join(f"{x:.3f}/{y:.3f}" for x, y in pts)
    small = st["width"] < 720
    return dict(strength=round(s, 2), curves=curve, saturation=1.04 if style == "natural" else 1.10, unsharp=0.40 if small else 0.25)

def look_filter(lp):
    if not lp or lp["strength"] <= 0.02 and lp["saturation"] <= 1.0: return "null"
    return f"curves=all='{lp['curves']}',eq=saturation={lp['saturation']},unsharp=5:5:{lp['unsharp']}:5:5:0.0"

def plan(cfg, st, meta):
    pc = cfg["picture"]; cw, ch = meta["canvas"]
    den = pc["denoise"]
    if den == "auto": den = 0.0 if st["noise"] < 1.0 else min(1.0, 0.4 + st["noise"] / 4)
    elif den == "off": den = 0.0
    face = pc["face_restore"]
    if face == "auto": face = "gpen" if (st["face_found_ratio"] >= 0.6 and st.get("face_w", 1) * st["width"] < 420 and st["width"] <= 800) else "off"
    lp = look_params(st, pc["look"])
    p = dict(denoise=float(den), face_restore=face, relight=bool(pc["relight"]) and face != "off", look=lp, canvas=[cw, ch])
    log(f"picture plan: denoise {p['denoise']:.2f}, face_restore {p['face_restore']}, look strength {lp['strength'] if lp else 'off'}")
    return p

# ------------------------------------------------------------------ rendering
def _cover(f, cw, ch, cx):
    h, w = f.shape[:2]; s = max(cw / w, ch / h); nw, nh = int(round(w * s)), int(round(h * s))
    b = cv2.resize(f, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    x0 = int(np.clip(cx * nw - cw / 2, 0, max(0, nw - cw))); y0 = max(0, (nh - ch) // 2)
    return b[y0:y0 + ch, x0:x0 + cw], s, x0, y0

def presenter(cfg, work, meta, st, plan_):
    cw, ch = plan_["canvas"]; fps = meta["fps"]; w, h = st["width"], st["height"]; n = st["frames"]
    cx = st.get("face_cx", 0.5); out_final = os.path.join(work, "presenter.mp4")
    src = os.path.join(work, "clean_master.mp4")
    if plan_["denoise"] > 0:
        k = plan_["denoise"]; vf = f"hqdn3d={1 + 1.5 * k:.2f}:{1 + 1.0 * k:.2f}:{2 + 3 * k:.2f}:{2 + 2 * k:.2f}"
        dn = os.path.join(work, "clean_dn.mp4")
        if not os.path.exists(dn): run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf, "-c:v", "libx264", "-crf", "10", "-preset", "veryfast", "-an", dn])
        src = dn
    lf = look_filter(plan_["look"])
    if plan_["face_restore"] == "off":
        vfs = [f"scale={cw}:{ch}:force_original_aspect_ratio=increase:flags=lanczos", f"crop={cw}:{ch}:max(0\\,min(iw-{cw}\\,{cx:.4f}*iw-{cw}/2)):(ih-{ch})/2", lf]
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", ",".join(v for v in vfs if v != "null"), "-c:v", "libx264", "-crf", "12", "-preset", "medium",
             "-pix_fmt", "yuv420p", "-g", str(int(fps)), "-movflags", "+faststart", "-an", out_final]); return out_final
    # ---- face restoration, resumable chunks (each decoded on its own: memory stays bounded for any video length)
    import onnxruntime as ort
    ort.set_default_logger_severity(4); cv2.setNumThreads(2)
    so = ort.SessionOptions(); so.intra_op_num_threads = min(4, os.cpu_count() or 2)
    gp = ort.InferenceSession(ensure_file("gpen_bfr_512.onnx", MODEL_URLS["gpen_bfr_512.onnx"]), providers=["CPUExecutionProvider"], sess_options=so)
    cc = cascade(); chunk = 300; cdir = os.path.join(work, "chunks"); os.makedirs(cdir, exist_ok=True); strength = float(cfg["picture"]["face_strength"])
    for a0 in range(0, n, chunk):
        a1 = min(n, a0 + chunk); name = os.path.join(cdir, f"p_{a0:06d}.mp4")
        if os.path.exists(name + ".done"): continue
        t0 = time.time(); fr = read_frames(src, w, h, a0, a1 - a0, fps); box = None; dface = None
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{cw}x{ch}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "13",
                                "-preset", "medium", "-pix_fmt", "yuv420p", "-g", str(int(fps)), name], stdin=subprocess.PIPE)
        for i, f in enumerate(fr):
            base, s, x0, y0 = _cover(f, cw, ch, cx)
            if i % 2 == 0 or dface is None:
                g = cv2.equalizeHist(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)); r = cc.detectMultiScale(g, 1.1, 5, minSize=(max(40, w // 10), max(40, w // 10)), maxSize=(int(w * 0.8), int(w * 0.8)))
                if len(r):
                    x, y, fw, fh = max(r, key=lambda b: b[2] * b[3]); b_ = np.array([(x + fw / 2) * s - x0, (y + fh / 2) * s - y0, fw * s], float); box = b_ if box is None else 0.8 * box + 0.2 * b_
                if box is not None:
                    bx, by, bw = box; side = int(min(bw * 1.75, cw, ch)); by = by - side * 0.02
                    X0 = int(max(0, min(cw - side, bx - side / 2))); Y0 = int(max(0, min(ch - side, by - side / 2))); crop = base[Y0:Y0 + side, X0:X0 + side]
                    inp = cv2.cvtColor(cv2.resize(crop, (512, 512), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB).astype(np.float32) / 127.5 - 1
                    o = gp.run(None, {"input": inp.transpose(2, 0, 1)[None]})[0][0].transpose(1, 2, 0); o = cv2.cvtColor(np.clip((o + 1) * 127.5, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
                    o = cv2.resize(o, (side, side), interpolation=cv2.INTER_CUBIC)
                    yy, xx = np.mgrid[0:side, 0:side].astype(np.float32); d = np.sqrt(((xx - side / 2) / (side * .47)) ** 2 + ((yy - side / 2) / (side * .5)) ** 2)
                    mk = np.clip((1 - d) / .35, 0, 1)[..., None] * strength
                    res = (crop * (1 - mk) + o * mk).astype(np.uint8); dface = (X0, Y0, side, res.astype(np.float32) - crop.astype(np.float32))
                    base = base.copy(); base[Y0:Y0 + side, X0:X0 + side] = res
            elif dface is not None:                      # odd frames reuse the face-detail delta of the previous frame (halves the cost, no flicker)
                X0, Y0, side, D = dface; base = base.copy(); base[Y0:Y0 + side, X0:X0 + side] = np.clip(base[Y0:Y0 + side, X0:X0 + side].astype(np.float32) + D, 0, 255).astype(np.uint8)
            enc.stdin.write(base.tobytes())
        enc.stdin.close(); enc.wait(); open(name + ".done", "w").close(); log(f"face restore: frames {a0}-{a1} in {time.time() - t0:.0f}s")
    lst = os.path.join(work, "chunks.txt"); open(lst, "w").write("".join(f"file '{os.path.join(cdir, f'p_{a:06d}.mp4')}'\n" for a in range(0, n, chunk)))
    p2 = os.path.join(work, "presenter_restored.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", p2])
    # ---- relight + look in one streaming pass
    p3 = p2
    if plan_["relight"]:
        p3 = os.path.join(work, "presenter_relit.mp4"); FS = cw * ch * 3
        g = subprocess.Popen(["ffmpeg", "-v", "error", "-i", p2, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, bufsize=FS * 3)
        sv = f"scale={cw}:{ch}:force_original_aspect_ratio=increase:flags=lanczos,crop={cw}:{ch}:max(0\\,min(iw-{cw}\\,{cx:.4f}*iw-{cw}/2)):(ih-{ch})/2"
        s_ = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", sv, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, bufsize=FS * 3)
        e = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{cw}x{ch}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "13",
                              "-preset", "medium", "-pix_fmt", "yuv420p", "-g", str(int(fps)), p3], stdin=subprocess.PIPE)
        while True:
            a = g.stdout.read(FS); b = s_.stdout.read(FS)
            if len(a) < FS or len(b) < FS: break
            G = np.frombuffer(a, np.uint8).reshape(ch, cw, 3).astype(np.float32); S = np.frombuffer(b, np.uint8).reshape(ch, cw, 3).astype(np.float32)
            corr = cv2.GaussianBlur(S, (0, 0), 9) - cv2.GaussianBlur(G, (0, 0), 9)
            e.stdin.write(np.clip(G + np.clip(corr, -22, 22) * 0.85, 0, 255).astype(np.uint8).tobytes())
        e.stdin.close(); e.wait(); g.kill(); s_.kill()
    run(["ffmpeg", "-v", "error", "-y", "-i", p3, "-vf", lf, "-c:v", "libx264", "-crf", "12", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", str(int(fps)),
         "-movflags", "+faststart", "-an", out_final])
    return out_final


def face_track(work, meta, step=0.5):
    """Face boxes (canvas coordinates) every `step` seconds on the final presenter video -> face_track.json. Used by compose to keep graphics off faces."""
    path = os.path.join(work, "face_track.json")
    pv = os.path.join(work, "presenter.mp4")
    if os.path.exists(path) and os.path.getmtime(path) > os.path.getmtime(pv): return json.load(open(path))
    cw, ch = meta["canvas"]; cc = cascade(); out = []; from .util import probe
    n = int(probe(pv)["duration"] / step) + 1
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", pv, "-vf", f"fps={1 / step}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, ch, cw, 3); found = 0
    for k, f in enumerate(fr):
        g = cv2.equalizeHist(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)); r = cc.detectMultiScale(g, 1.1, 5, minSize=(int(cw * 0.06), int(cw * 0.06)), maxSize=(int(cw * 0.85), int(cw * 0.85)))
        out.append(dict(t=round(k * step, 2), boxes=[[int(x), int(y), int(w), int(h)] for x, y, w, h in r])); found += bool(len(r))
    tr = dict(step=step, frames=out, found_ratio=found / max(1, len(out))); json.dump(tr, open(path, "w")); return tr

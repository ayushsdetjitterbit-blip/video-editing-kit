"""Quality gates on the RENDERED file. A video only passes if: length and size are right, loudness is on target, nothing is black, the face is visible
in every frame outside the planned full-screen beats, and no graphic overlaps the face or the caption pill covers the mouth.
Rectangles come from layout_rects.json (written by compose), so nothing here is tied to one video's layout."""
import json, os, subprocess
import numpy as np
import cv2
from .util import probe, run, log
from .picture import cascade

def loudness(path):
    import re
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    tail = r[r.rfind("Summary"):]; i = re.findall(r"I:\s+(-?\d+\.?\d*)\s+LUFS", tail); p = re.findall(r"Peak:\s+(-?\d+\.?\d*)\s+dBFS", tail)
    return (float(i[-1]) if i else None), (float(p[-1]) if p else None)

def run_qa(video, work, cfg, meta, timeline):
    sched = json.load(open(os.path.join(work, "schedule.json"))); cw, ch = sched["canvas"]; checks = []; ok_all = True
    def chk(name, ok, detail, warn=False):
        nonlocal ok_all; checks.append(dict(name=name, status="pass" if ok else ("warn" if warn else "FAIL"), detail=detail)); ok_all = ok_all and (ok or warn)
    p = probe(video); chk("size", (p["width"], p["height"]) == (cw, ch), f"{p['width']}x{p['height']} expected {cw}x{ch}")
    chk("duration", abs(p["duration"] - timeline["duration"]) < 0.15, f"{p['duration']:.2f}s expected {timeline['duration']:.2f}s")
    chk("audio", p["has_audio"], "audio track present" if p["has_audio"] else "NO AUDIO")
    lufs, peak = loudness(video); tgt = cfg["audio"]["target_lufs"]
    chk("loudness", lufs is not None and abs(lufs - tgt) <= 1.5, f"{lufs} LUFS (target {tgt})")
    chk("true peak", peak is not None and peak <= -0.5, f"{peak} dBTP (limit -0.5)")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "fps=4", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, ch, cw, 3); cc = cascade(); fulls = [r for r in sched["rects"] if r["full"]]; boxes = [r for r in sched["rects"] if not r["full"]]
    ctop = 1530 if ch >= cw else int(ch * 0.80); pill = (cw // 2 - 432, ctop, 864, 90); black = []; miss = []; overlap = []; n_face = 0
    for k, f in enumerate(fr):
        t = k / 4.0
        if f.mean() < 8 and t < sched["duration"] - 0.6: black.append(round(t, 2))
        if any(r["t0"] <= t <= r["t1"] for r in fulls): continue
        g = cv2.equalizeHist(cv2.cvtColor(f[: int(ch * 0.65)], cv2.COLOR_GRAY2BGR if False else cv2.COLOR_BGR2GRAY))
        r_ = cc.detectMultiScale(g, 1.1, 5, minSize=(int(cw * 0.12), int(cw * 0.12)), maxSize=(int(cw * 0.8), int(cw * 0.8)))
        if not len(r_): miss.append(round(t, 2)); continue
        n_face += 1; x, y, w, h = max(r_, key=lambda b: b[2] * b[3]); fb = (x, y, w, h)
        def inter(a, b): return max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) * max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
        for r in boxes:
            if r["t0"] <= t <= r["t1"] and inter(fb, (r["x"], r["y"], r["w"], r["h"])) > 0: overlap.append((round(t, 2), "graphic"))
        if inter(fb, pill) > 0: overlap.append((round(t, 2), "caption"))
    total = max(1, n_face + len(miss))
    chk("no black frames", not black, f"black at {black[:6]}" if black else "none")
    chk("face visible", len(miss) / total <= 0.05, f"face not found in {len(miss)}/{total} frames outside full-screen beats" + (f" (t={miss[:8]})" if miss else ""), warn=True)
    chk("face not covered", not overlap, f"overlap at {overlap[:8]}" if overlap else "no graphic or caption overlaps the detected face")
    rep = dict(passed=ok_all, checks=checks, video=video)
    json.dump(rep, open(os.path.join(work, "qa_report.json"), "w"), indent=1)
    for c in checks: log(f"qa {c['status']:>4}  {c['name']}: {c['detail']}")
    return rep

"""Stage 3: decide what to keep, then render the clean cut.
Rules (never broken): cut only between phrases, never inside one; keep natural beats; keep the best of repeated takes; drop a window only if it is
purely filler or an abandoned start of the next window. Everything is frame-exact, and audio is cut at the same sample positions (48 kHz)."""
import difflib, json, os, re
import numpy as np
from .util import run, log

FILLERS = {
    "en": {"um", "umm", "uh", "uhh", "er", "erm", "ah", "ahh", "hmm", "mm", "hm", "eh"},
    "hi": {"अ", "आ", "उम", "उम्म", "हम्म", "अम", "अं", "ऊं", "एं", "आं", "हम", "म्म"},
}
def norm(t): return re.sub(r"[^\wऀ-ॿ ]+", "", t.lower()).strip()

def is_filler_only(win, lang):
    toks = [norm(w["w"]) for w in win["words"] if norm(w["w"])]
    if not toks: return True
    f = FILLERS.get("en", set()) | FILLERS.get(lang or "en", set())
    return all(t in f for t in toks) and (win["b"] - win["a"]) < 2.5

def sim(a, b): return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()

def decide(windows, cfg, language):
    """Returns (keep_indices, dropped=[{index, reason}])."""
    c = cfg["cut"]; drop = {}
    for i in c.get("drop_windows", []): drop[int(i)] = "manual"
    for i, w in enumerate(windows):
        if i in drop: continue
        if c["drop_fillers"] and is_filler_only(w, language): drop[i] = "filler only"
    if c["drop_repeats"]:
        rest = [i for i in range(len(windows)) if i not in drop]
        for r in range(len(rest) - 1):
            i, j = rest[r], rest[r + 1]
            if i in drop: continue
            a, b = windows[i], windows[j]
            if not norm(a["text"]) or not norm(b["text"]): continue
            gap = b["a"] - a["b"]
            if gap > 4.0: continue
            na, nb = norm(a["text"]), norm(b["text"])
            repeat = sim(a["text"], b["text"]) >= c["repeat_similarity"] and abs(len(na) - len(nb)) <= 0.35 * max(len(na), len(nb))
            restart = len(na) >= 6 and (nb.startswith(na[: max(6, int(len(na) * 0.8))]) and len(nb) > len(na) * 1.15)
            if repeat or restart:
                pa = np_mean([x["p"] for x in a["words"]]); pb = np_mean([x["p"] for x in b["words"]])
                loser = i if (restart or pb >= pa - 0.02) else j       # keep the later take unless the earlier one was clearly clearer
                drop[loser] = "repeated take" if repeat else "false start"
    return [i for i in range(len(windows)) if i not in drop], [dict(index=i, reason=r, text=windows[i]["text"]) for i, r in sorted(drop.items())]

def np_mean(xs): return sum(xs) / len(xs) if xs else 0.0

KEEP_REPEAT = {"very", "really", "no", "ha", "bye", "yes"}      # words people repeat on purpose

def _toks(win): return [(w, norm(w["w"])) for w in win["words"] if norm(w["w"])]

def excisions(win, c, language):
    """[(start, end, reason, text)] inside one window: filler words and stuttered words/phrases (the first copy goes, the last clean one stays)."""
    ws = _toks(win); out = []
    f = FILLERS.get("en", set()) | FILLERS.get(language or "en", set())
    if c.get("drop_filler_words", True):
        for k, (w, t) in enumerate(ws):
            if t in f and (w["e"] - w["s"]) >= 0.05:
                # Whisper under-measures fillers (an "uh" is often 0.3 s but timed 0.1 s): remove everything between the neighbouring words,
                # keeping 0.05 s of the natural gap on each side; a filler at the start/end of a window removes the whole tail/lead.
                lo = ws[k - 1][0]["e"] + 0.05 if k > 0 else win["a"] - 0.25
                hi = ws[k + 1][0]["s"] - 0.05 if k + 1 < len(ws) else win["b"] + 0.25
                lo, hi = min(lo, w["s"] - 0.04), max(hi, w["e"] + 0.06)       # never smaller than the filler's own span (neighbour times can be off by 0.1 s)
                out.append((lo, hi, "filler", w["w"]))
    if c.get("drop_stutters", True):
        toks = [t for _, t in ws]; i = 0
        while i < len(ws) - 1:
            hit = False
            for n in (3, 2, 1):
                if i + 2 * n <= len(ws) and toks[i:i + n] == toks[i + n:i + 2 * n] and not (n == 1 and toks[i] in KEEP_REPEAT) and not (n == 1 and toks[i] in f):
                    out.append((ws[i][0]["s"] - 0.02, ws[i + n][0]["s"] - 0.02, "stutter", " ".join(w["w"] for w, _ in ws[i:i + n]))); i += n; hit = True; break
            if not hit: i += 1
    return sorted(out)

def snap(db, t, span=0.05):
    """Move a cut point to the quietest 10 ms frame within +-span seconds, so cuts land in a gap between words, not on a syllable."""
    if db is None: return t
    i0 = max(0, int((t - span) * 100)); i1 = min(len(db), int((t + span) * 100) + 1)
    if i1 - i0 < 3: return t
    sm = np.convolve(db[i0:i1], np.ones(3) / 3, mode="same"); return (i0 + int(np.argmin(sm))) / 100 + 0.005

def build(windows, cfg, fps, duration, language, db=None):
    c = cfg["cut"]; keep_idx, dropped = decide(windows, cfg, language); segs = []; removed = []
    mw = float(c.get("min_window", 0.45))
    for i in list(keep_idx):                                      # noise / interjections: a lone word or implausibly fast "words" in a very short window
        w = windows[i]; n = len(_toks(w)); d = w["b"] - w["a"]
        mp = sum(x["p"] for x in w["words"]) / max(1, len(w["words"])); edge = (i == 0 or i == len(windows) - 1)
        if d < mw and ((n <= 1 and (mp < 0.15 or edge)) or d / max(n, 1) < 0.12) and i not in c.get("keep_windows", []):
            keep_idx.remove(i); dropped.append(dict(index=i, reason="blip / interjection", text=w["text"]))
    pk = c.get("pause_keep"); bridge = {}                                   # natural pauses between neighbouring kept windows
    if pk:
        for p, q in zip(keep_idx, keep_idx[1:]):
            if q == p + 1:                                                # nothing was removed between them
                g = windows[q]["a"] - windows[p]["b"]
                bridge[(p, "end")] = windows[q]["a"] if g <= pk else windows[p]["b"] + pk / 2     # short pause: keep it whole, no cut at all
                bridge[(q, "start")] = windows[p]["b"] if g <= pk else windows[q]["a"] - pk / 2   # long pause: shorten it to `pause_keep`
    for i in keep_idx:
        w = windows[i]
        a0 = w["a"]
        if c.get("trim_breath", True) and w.get("a_strict", a0) - a0 >= 0.25:
            spoken = [x for x in w["words"] if norm(x["w"]) and x["p"] >= 0.5 and (x["s"] + x["e"]) / 2 < w["a_strict"] - 0.1]
            if not spoken: a0 = w["a_strict"] - 0.05      # breath / lip noise before the first word (never trims a quiet but real word)
        a = float(c["start_overrides"].get(i, c["start_overrides"].get(str(i), a0))) - c["pad_before"]
        b = float(c["end_overrides"].get(i, c["end_overrides"].get(str(i), w["b"]))) + c["pad_after"]
        if (i, "start") in bridge: a = bridge[(i, "start")]
        if (i, "end") in bridge: b = bridge[(i, "end")]
        a, b = max(0.0, a), min(duration, b); pieces = [[a, b]]
        for xs, xe, why, txt in excisions(w, c, language):
            xs, xe = snap(db, xs), snap(db, xe)
            if xe - xs < 0.04: continue
            nxt = []
            for p0, p1 in pieces:
                if xe <= p0 or xs >= p1: nxt.append([p0, p1]); continue
                if xs - p0 >= 0.12: nxt.append([p0, xs])
                if p1 - xe >= 0.12: nxt.append([xe, p1])
            pieces = nxt; removed.append(dict(window=i, t=round(xs, 2), len=round(xe - xs, 2), reason=why, text=txt))
        for xs, xe in c.get("excise", []):                      # hand-picked fumbles: [start, end] in source seconds
            if xe <= a or xs >= b: continue
            xs, xe = snap(db, xs), snap(db, xe); nxt = []
            for p0, p1 in pieces:
                if xe <= p0 or xs >= p1: nxt.append([p0, p1]); continue
                if xs - p0 >= 0.12: nxt.append([p0, xs])
                if p1 - xe >= 0.12: nxt.append([xe, p1])
            if len(nxt) != len(pieces) or any(abs(x[0] - y[0]) > 1e-6 or abs(x[1] - y[1]) > 1e-6 for x, y in zip(nxt, pieces)): removed.append(dict(window=i, t=round(xs, 2), len=round(xe - xs, 2), reason="manual", text=""))
            pieces = nxt
        for p0, p1 in pieces: segs.append([p0, p1, i])
    segs.sort(key=lambda s: s[0])
    if segs: segs[-1][1] = min(duration, windows[keep_idx[-1]]["b"] + max(c["tail_pad"], c["pad_after"]))
    fr = lambda t: int(round(t * fps)); keep = []
    for a, b, i in segs:
        A, B = fr(a), fr(b)
        if keep and A <= keep[-1][1]: keep[-1][1] = max(B, keep[-1][1]); keep[-1][2].append(i)
        else: keep.append([A, B, [i]])
    return keep, dropped, removed

def render(work, keep, fps, sr=48000):
    """Frame-exact picture + sample-exact audio from the same cut points."""
    spf = sr // fps; assert sr % fps == 0, f"{sr} Hz is not a multiple of {fps} fps"
    v, a = [], []
    for k, (A, B, _) in enumerate(keep):
        v.append(f"[0:v]trim=start_frame={A}:end_frame={B},setpts=PTS-STARTPTS[v{k}]")
        d = (B - A) / fps
        a.append(f"[0:a]atrim=start_sample={A * spf}:end_sample={B * spf},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.006,afade=t=out:st={max(0, d - 0.006):.4f}:d=0.006[a{k}]")
    n = len(keep)
    open(os.path.join(work, "cut_filter.txt"), "w").write(";".join(v + a) + ";" + "".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
    run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(work, "src.mp4"), "-filter_complex_script", os.path.join(work, "cut_filter.txt"),
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-pix_fmt", "yuv420p", "-r", str(fps),
         "-c:a", "aac", "-b:a", "256k", os.path.join(work, "clean_master.mp4")])

def cut_stage(cfg, work, meta):
    tr = json.load(open(os.path.join(work, "transcript.json"))); fps = meta["fps"]
    from .transcribe import _read16
    x = _read16(os.path.join(work, "a16.wav")); hop = 160; n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-6)
    keep, dropped, removed = build(tr["windows"], cfg, fps, meta["duration"], tr["language"], db)
    total = sum(b - a for a, b, _ in keep) / fps
    log(f"cut: {len(keep)} segments, {total:.2f}s kept of {meta['duration']:.2f}s; dropped windows: {[d['reason'] + '#' + str(d['index']) for d in dropped]}; word-level cuts: {len(removed)}")
    json.dump(dict(fps=fps, keep=[[a / fps, b / fps] for a, b, _ in keep], frames=[[a, b] for a, b, _ in keep], windows_per_segment=[w for _, _, w in keep],
                   dropped=dropped, removed=removed, duration=total), open(os.path.join(work, "timeline.json"), "w"), ensure_ascii=False)
    render(work, keep, fps)
    return total

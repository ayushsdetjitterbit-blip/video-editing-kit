"""Stage 3: decide what to keep, then render the clean cut.
Rules (never broken): cut only between phrases, never inside one; keep natural beats; keep the best of repeated takes; drop a window only if it is
purely filler or an abandoned start of the next window. Everything is frame-exact, and audio is cut at the same sample positions (48 kHz)."""
import difflib, json, os, re
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

def build(windows, cfg, fps, duration, language):
    c = cfg["cut"]; keep_idx, dropped = decide(windows, cfg, language); segs = []
    for i in keep_idx:
        w = windows[i]
        a0 = w["a"]
        if c.get("trim_breath", True) and w.get("a_strict", a0) - a0 >= 0.25: a0 = w["a_strict"] - 0.05      # breath / lip noise before the first word
        a = float(c["start_overrides"].get(i, c["start_overrides"].get(str(i), a0))) - c["pad_before"]
        b = float(c["end_overrides"].get(i, c["end_overrides"].get(str(i), w["b"]))) + c["pad_after"]
        segs.append([max(0.0, a), min(duration, b), i])
    if segs: segs[-1][1] = min(duration, windows[keep_idx[-1]]["b"] + max(c["tail_pad"], c["pad_after"]))
    fr = lambda t: int(round(t * fps)); keep = []
    for a, b, i in segs:
        A, B = fr(a), fr(b)
        if keep and A <= keep[-1][1]: keep[-1][1] = max(B, keep[-1][1]); keep[-1][2].append(i)
        else: keep.append([A, B, [i]])
    return keep, dropped

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
    keep, dropped = build(tr["windows"], cfg, fps, meta["duration"], tr["language"])
    total = sum(b - a for a, b, _ in keep) / fps
    log(f"cut: {len(keep)} segments, {total:.2f}s kept of {meta['duration']:.2f}s; dropped windows: {[d['reason'] + '#' + str(d['index']) for d in dropped]}")
    json.dump(dict(fps=fps, keep=[[a / fps, b / fps] for a, b, _ in keep], frames=[[a, b] for a, b, _ in keep], windows_per_segment=[w for _, _, w in keep],
                   dropped=dropped, duration=total), open(os.path.join(work, "timeline.json"), "w"), ensure_ascii=False)
    render(work, keep, fps)
    return total

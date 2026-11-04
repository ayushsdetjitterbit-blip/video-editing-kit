"""Captions: chunk the transcript into 1-4 word groups on phrase boundaries, timed from real word timestamps and mapped to the cut timeline.
Whisper's spelling is unreliable for Hindi/Hinglish or names, so a `captions.corrections` map (wrong -> right, applied per word or phrase) and an
editable draft file (captions_draft.yaml) are supported: edit the text, keep the times, re-run."""
import json, os, re
import yaml

def mapper(timeline):
    """source seconds -> cut timeline seconds."""
    keep = timeline["keep"]; off = []; a = 0.0
    for s, e in keep: off.append(a); a += e - s
    def M(t):
        for (s, e), o in zip(keep, off):
            if s - 1e-6 <= t <= e + 1e-6: return round(o + t - s, 3)
        for (s, e), o in zip(keep, off):
            if t < s: return round(o, 3)
        return round(a, 3)
    return M

def _apply_corrections(text, corr):
    for wrong, right in (corr or {}).items(): text = re.sub(re.escape(wrong), right, text, flags=re.IGNORECASE)
    return text

def chunks_from_transcript(transcript, timeline, cfg, windows_kept):
    """[(src_start, text, src_end_of_window)] using whisper words; skips dropped windows."""
    cc = cfg["captions"]; out = []
    for wi in windows_kept:
        w = transcript["windows"][wi]; words = [x for x in w["words"] if x["w"]]
        cur = []
        def flush():
            if cur:
                txt = _apply_corrections(" ".join(x["w"] for x in cur), cc["corrections"]); out.append((cur[0]["s"], txt, w["b"]))
        for x in words:
            cur.append(x); full = len(cur) >= cc["max_words"] or len(" ".join(y["w"] for y in cur)) >= cc["max_chars"]
            if full or x["w"].endswith((",", ".", "?", "!", "।", ";")): flush(); cur = []
        flush()
    return out

def chunks_from_file(path, transcript):
    """Hand-corrected caption chunks: a YAML list of {t: source_seconds, text: "..."} (t = when the first word is spoken).
    Use this when Whisper's spelling is too poor (Hindi/Hinglish, names, technical terms). Words are timed proportionally inside each chunk."""
    ch = yaml.safe_load(open(path)) or []; wins = transcript["windows"]; out = []
    for c in sorted(ch, key=lambda c: float(c["t"])):
        t = float(c["t"]); w = next((w for w in wins if w["a"] - 0.3 <= t <= w["b"] + 0.3), None)
        out.append((t, str(c["text"]), (w["b"] if w else t + 2.0)))
    return out

def build_groups(chunks, M, dur, fps):
    """Turn chunks into timed word groups on the cut timeline; every word's start is proportional to its length inside the chunk's time span."""
    groups = []
    for k, (t0, txt, wend) in enumerate(chunks):
        words = txt.split()
        if not words: continue
        nxt = chunks[k + 1][0] if k + 1 < len(chunks) else wend
        end = min(nxt, t0 + 0.30 * len(words) + 0.5, wend + 0.05) if nxt > t0 else t0 + 0.5
        end = max(end, t0 + 0.25); L = [max(len(w), 2) for w in words]; tot = sum(L); acc = t0; st = []
        for l in L: st.append(M(acc)); acc += (end - t0) * l / tot
        groups.append(dict(words=words, st=st, t0=M(t0), end=M(end)))
    for k, g in enumerate(groups):
        nxt = groups[k + 1]["st"][0] if k + 1 < len(groups) else dur
        t1 = min(g["end"] + 0.05, nxt - 0.02) if nxt > g["end"] else g["end"]
        if t1 <= g["st"][-1]: t1 = g["st"][-1] + 0.3
        g["t0"] = round(max(0.05, g["st"][0] - 0.05), 3); g["t1"] = round(min(t1, dur - 0.04), 3); g["st"] = [round(x, 3) for x in g["st"]]; g.pop("end")
    return groups

def write_draft(work, groups):
    json_path = os.path.join(work, "captions_draft.yaml")
    yaml.safe_dump([dict(t=g["st"][0], text=" ".join(g["words"])) for g in groups], open(json_path, "w"), allow_unicode=True, sort_keys=False)
    return json_path

def apply_draft(groups, work):
    """If captions_edited.yaml exists (same length/times as the draft), use its text with the original timings."""
    p = os.path.join(work, "captions_edited.yaml")
    if not os.path.exists(p): return groups
    ed = yaml.safe_load(open(p)) or []
    if len(ed) != len(groups): return groups
    for g, e in zip(groups, ed):
        w = str(e["text"]).split()
        if not w: continue
        L = [max(len(x), 2) for x in w]; tot = sum(L); span = max(0.3, g["t1"] - g["t0"] - 0.1); acc = g["t0"] + 0.05; st = []
        for l in L: st.append(round(acc, 3)); acc += span * l / tot
        g["words"], g["st"] = w, st
    return groups

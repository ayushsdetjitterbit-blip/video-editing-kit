"""Stage 2: find speech runs/pauses from audio energy, then transcribe every phrase window separately.
(Whisper large-v3 silently drops text in windows longer than ~30 s, so long recordings are never fed in one piece.)"""
import json, os, wave
import numpy as np
from .util import log

def _read16(path):
    w = wave.open(path); return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768

def speech_runs(a16_path, min_gap=0.08):
    """[(start, end)] seconds of speech. Threshold = measured room noise + 8 dB (never a fixed level), so quiet and loud recordings both work."""
    x = _read16(a16_path); hop = 160; n = len(x) // hop
    if n < 10: return []
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-6)
    floor = np.percentile(db, 10); thr = max(floor + 8, -55 if floor < -60 else -48)
    thr = min(thr, np.percentile(db, 90) - 12)          # keep the threshold below the speech level even in noisy rooms
    sp = db > thr; runs, s = [], None
    for i, v in enumerate(sp):
        if v and s is None: s = i
        if not v and s is not None: runs.append([s, i]); s = None
    if s is not None: runs.append([s, len(sp)])
    m = []
    for a, b in runs:
        if m and (a - m[-1][1]) < int(min_gap * 100): m[-1][1] = b
        else: m.append([a, b])
    return [(a / 100, b / 100) for a, b in m if b - a >= 8]

def strict_edges(a16_path, wins):
    """For each window, where *voiced* speech really starts/ends (energy well above the room noise). A breath or lip noise before the first word shows up as a
    large gap between the loose edge (used for transcription) and the strict edge; the cut stage trims it when the gap is >= 0.25 s."""
    x = _read16(a16_path); hop = 160; n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-6); thr = np.percentile(db, 10) + 16; out = []
    for a, b in wins:
        seg = db[int(a * 100):int(b * 100)]; idx = np.where(seg > thr)[0]
        out.append((a + idx[0] / 100, a + idx[-1] / 100) if len(idx) else (a, b))
    return out

def windows(runs, pause_min):
    """Group speech runs into phrase windows split at pauses >= pause_min."""
    out = []
    for a, b in runs:
        if out and a - out[-1][1] < pause_min: out[-1][1] = b
        else: out.append([a, b])
    return out

def has_loop(words, times=3, ns=(1, 2, 3, 4, 5, 6)):
    """Whisper sometimes loops on one phrase ('X ke liye X ke liye X ke liye ...'). True if any n-gram (1-6 words) repeats `times`+ times in a row."""
    t = [w["w"].strip().lower() for w in words]
    for n in ns:
        for k in range(len(t) - n * times + 1):
            g = t[k:k + n]
            if (n > 1 or len(g[0]) > 1) and all(t[k + j * n:k + (j + 1) * n] == g for j in range(times)): return True
    return False

def collapse_loops(words, ns=(6, 5, 4, 3, 2, 1), times=3):
    """Keep the first occurrence of a looping phrase (repeated `times`+ times in a row); normal doubles ('really really') are left alone."""
    out = list(words); key = lambda ws: [w["w"].strip().lower() for w in ws]
    for n in ns:
        k = 0
        while k + n * times <= len(out):
            g = key(out[k:k + n]); r = 1
            while k + (r + 1) * n <= len(out) and key(out[k + r * n:k + (r + 1) * n]) == g: r += 1
            if r >= times and (n > 1 or len(g[0]) > 1): del out[k + n:k + r * n]
            k += 1
    return out

def transcribe(work, language="auto", pause_min=0.25, model_size="large-v3"):
    a16 = os.path.join(work, "a16.wav"); x = _read16(a16)
    runs = speech_runs(a16); win = windows(runs, pause_min)
    strict = strict_edges(a16, win)
    log(f"transcribe: {len(runs)} speech runs, {len(win)} phrase windows")
    from faster_whisper import WhisperModel
    m = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    lang = None if language == "auto" else language
    out = []; detected = None
    for k, (a, b) in enumerate(win):
        A = max(0, a - 0.15); B = min(len(x) / 16000, b + 0.15)
        def go(temps, beam):
            return m.transcribe(x[int(A * 16000):int(B * 16000)], language=lang or detected, word_timestamps=True, vad_filter=False, condition_on_previous_text=False,
                                beam_size=beam, temperature=temps, compression_ratio_threshold=2.0)
        seg, info = go(0, 5); seg = list(seg)
        if has_loop([dict(w=q.word) for s_ in seg for q in s_.words]):            # hallucinated loop: retry with sampling, then collapse what is left
            log(f"  window {k}: repeated-phrase loop detected, retrying"); seg, info = go((0.2, 0.4, 0.6), 1); seg = list(seg)
        if lang is None and detected is None:
            detected = info.language                                           # decide the language once, from the first phrase
            if detected == "ur": log("WARNING: detected Urdu. Hindi/Hinglish speech is often detected as Urdu - if this video is Hindi, set `language: hi` in config.yaml")
        ws = [dict(w=q.word.strip(), s=round(A + q.start, 2), e=round(A + q.end, 2), p=round(q.probability, 2)) for s_ in seg for q in s_.words]
        if has_loop(ws): ws = collapse_loops(ws); log(f"  window {k}: loop collapsed to one occurrence")
        out.append(dict(a=round(a, 2), b=round(b, 2), a_strict=round(strict[k][0], 2), b_strict=round(strict[k][1], 2), words=ws, text=" ".join(q["w"] for q in ws)))
        if k % 5 == 0: log(f"  window {k + 1}/{len(win)}")
    json.dump(dict(language=lang or detected, windows=out), open(os.path.join(work, "transcript.json"), "w"), ensure_ascii=False, indent=1)
    return out

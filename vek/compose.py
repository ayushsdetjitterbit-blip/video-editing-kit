"""Stage 6: turn (cut timeline + captions + storyboard) into a HyperFrames project and render it.

Layout is expressed in a 1080x1920 design space (the vertical canvas). Rules that keep every video safe:
  - the presenter is always full frame and is never moved or shrunk;
  - cards / lists / tiles sit BELOW the chin (top >= 1056); captions sit at 1530; the top 168 px stay clear;
  - only `broll` and `still` beats cover the whole screen (the face is hidden on purpose, only for those beats);
  - every element's rectangle and time range is written to layout_rects.json so QA can prove the face is never covered.
"""
import json, os, re, shutil, subprocess
import yaml
from .captions import mapper
from .util import log, run

ACCENT = "#0A84FF"
CSS = """
  @font-face { font-family: 'Deva'; src: url('assets/fonts/NotoSansDevanagari-800.woff2') format('woff2'); font-weight: 100 900; unicode-range: U+0900-097F, U+200C-200D, U+25CC; }
  #root { position: absolute; inset: 0; font-family: 'Inter', 'Deva', sans-serif; color: #fff; }
  .glass { background: rgba(28,28,30,.78); backdrop-filter: blur(30px) saturate(180%); border: 1.5px solid rgba(255,255,255,.16); box-shadow: 0 18px 50px rgba(0,0,0,.26); }
  .fcard { position: absolute; left: 60px; top: 1072px; width: 960px; height: 164px; border-radius: 46px; opacity: 0; display: flex; align-items: center; gap: 28px; padding: 0 32px; overflow: hidden; }
  .fic { flex: none; width: 104px; height: 104px; border-radius: 30px; display: flex; align-items: center; justify-content: center; }
  .fic svg { width: 60px; height: 60px; }
  .shim { position: absolute; top: -20px; bottom: -20px; left: 0; width: 220px; background: linear-gradient(100deg, rgba(255,255,255,0) 0%, rgba(255,255,255,.22) 50%, rgba(255,255,255,0) 100%); pointer-events: none; }
  .ftx { flex: 1 1 auto; min-width: 0; }
  .ft { font-weight: 800; font-size: 54px; line-height: 1.08; letter-spacing: -0.02em; white-space: nowrap; }
  .fs { font-weight: 600; font-size: 33px; line-height: 1.2; margin-top: 6px; color: rgba(235,235,245,.66); white-space: nowrap; }
  .pw { position: absolute; left: 36px; width: 1008px; height: 448px; transform-origin: 50% 0; }
  .pw .pcard { top: 0; left: 0; }
  .pcard { position: absolute; left: 36px; top: 1056px; width: 1008px; height: 448px; border-radius: 48px; overflow: hidden; opacity: 0; }
  .pcard.glass { background: rgba(22,22,24,.94); }
  .chipl { position: absolute; left: 22px; top: 22px; height: 70px; padding: 0 28px 0 14px; border-radius: 35px; display: flex; align-items: center; gap: 14px; font-weight: 800; font-size: 34px; letter-spacing: -0.01em; white-space: nowrap; }
  .chipl .dot { width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
  .chipl .dot svg { width: 28px; height: 28px; }
  .hdr { position: absolute; left: 44px; top: 22px; font-weight: 800; font-size: 54px; letter-spacing: -0.02em; }
  .row { position: absolute; left: 44px; right: 44px; height: 64px; display: flex; align-items: center; gap: 26px; opacity: 0; }
  .rb { flex: none; width: 48px; height: 48px; border-radius: 50%; border: 4px solid rgba(235,235,245,.38); display: flex; align-items: center; justify-content: center; }
  .rb svg { width: 28px; height: 28px; opacity: 0; }
  .rt { font-weight: 700; font-size: 42px; letter-spacing: -0.01em; white-space: nowrap; }
  .tile { position: absolute; top: 24px; width: 470px; height: 400px; border-radius: 42px; opacity: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
  .tile .tt { font-weight: 900; font-size: 56px; letter-spacing: -0.02em; margin-top: 10px; line-height: 1.05; }
  .tile .ts { font-weight: 600; font-size: 32px; margin-top: 8px; color: rgba(255,255,255,.82); }
  .fsb { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; opacity: 0; overflow: hidden; background: #111; }
  .fsb video { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; object-position: var(--pos, 50% 50%); }
  .fshade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,.30) 0%, rgba(0,0,0,0) 22%, rgba(0,0,0,0) 48%, rgba(0,0,0,.62) 100%); }
  .fst { position: absolute; left: 48px; right: 48px; top: 1210px; }
  .fstt { font-weight: 900; font-size: 84px; letter-spacing: -0.03em; line-height: 1.04; text-shadow: 0 4px 30px rgba(0,0,0,.45); }
  .fsts { font-weight: 700; font-size: 40px; margin-top: 10px; color: rgba(255,255,255,.9); text-shadow: 0 2px 16px rgba(0,0,0,.5); }
"""
def _sv(body, sw=2.6, fill="none"): return f'<svg viewBox="0 0 24 24" fill="{fill}" stroke="#fff" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
ICON = {
  "drop": _sv('<path d="M12 2.8c3.5 4.4 6 7.2 6 10.6a6 6 0 0 1-12 0c0-3.4 2.5-6.2 6-10.6z" fill="#fff" stroke="none"/>'),
  "check": _sv('<path d="M5 12.8l4.6 4.6L19 7.6"/>', 3.2),
  "warn": _sv('<path d="M12 3.4L21.8 20.4H2.2z" fill="#fff" stroke="none"/><path d="M12 9.4v5" stroke="#FF453A" stroke-width="2.6"/><circle cx="12" cy="17.2" r="1.3" fill="#FF453A" stroke="none"/>'),
  "user": _sv('<circle cx="12" cy="8" r="4" fill="#fff" stroke="none"/><path d="M4.5 20.5c.8-4 3.7-6 7.5-6s6.7 2 7.5 6z" fill="#fff" stroke="none"/>'),
  "shield": _sv('<path d="M12 2.8l7.5 2.8v6c0 4.8-3.2 8.3-7.5 9.7-4.3-1.4-7.5-4.9-7.5-9.7v-6z" fill="#fff" stroke="none"/><path d="M8.5 12.2l2.4 2.4 4.6-4.8" stroke="#0A84FF" stroke-width="2.6"/>'),
  "bulb": _sv('<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V16h5v-.1c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z"/>', 2.2),
  "cal": _sv('<rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M3.5 10h17M8 3v4M16 3v4"/>'),
  "heart": _sv('<path d="M12 20.5s-7.5-4.6-7.5-10A4.3 4.3 0 0 1 12 7.8a4.3 4.3 0 0 1 7.5 2.7c0 5.4-7.5 10-7.5 10z" fill="#fff" stroke="none"/>'),
  "lab": _sv('<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3"/>', 2.2),
  "doc": _sv('<rect x="5" y="3.5" width="14" height="17" rx="3"/><path d="M8.5 9h7M8.5 13h7M8.5 17h4"/>', 2.2),
  "pill": _sv('<rect x="2.8" y="8.5" width="18.4" height="7" rx="3.5" transform="rotate(-40 12 12)"/><path d="M9.2 14.8l5.6-5.6"/>', 2.2),
  "stetho": _sv('<path d="M6 3v6a4 4 0 0 0 8 0V3M10 13v2a4 4 0 0 0 8 0v-1"/><circle cx="18" cy="12" r="2"/>', 2.2),
  "bubble": _sv('<path d="M4 5.5h16v11H11.5L7 20v-3.5H4z" fill="#fff" stroke="none"/>'),
  "wave": _sv('<path d="M3 12c2-4 4-4 6 0s4 4 6 0 4-4 6 0"/>', 2.6),
  "star": _sv('<path d="M12 3l2.7 5.8 6.3.8-4.6 4.4 1.2 6.3L12 17.2 6.4 20.3l1.2-6.3L3 9.6l6.3-.8z" fill="#fff" stroke="none"/>'),
  "play": _sv('<path d="M8 5l11 7-11 7z" fill="#fff" stroke="none"/>'),
  "chart": _sv('<path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/>', 2.6),
  "mic": _sv('<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>', 2.4),
  "flame": _sv('<path d="M12 3c1 3.5 5 5.5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4 .3 1.6 1 2 2 2-.5-3 .5-5.5 1-8z" fill="#fff" stroke="none"/>'),
}
BEAT_TYPES = ("card", "broll", "checklist", "tiles", "term", "follow", "still")

class StoryboardError(ValueError): pass

def _norm(t): return re.sub(r"[^\wऀ-ॿ]+", "", t.lower())

class Resolver:
    """Resolve `at`/`until` (source seconds) or `say`/`for` (find these words in the transcript) to cut-timeline seconds."""
    def __init__(self, transcript, M, dur):
        self.M, self.dur = M, dur
        self.words = [(x["s"], x["e"], _norm(x["w"])) for w in transcript["windows"] for x in w["words"] if _norm(x["w"])]
    def find(self, phrase, after=0.0):   # `after` is in cut-timeline seconds
        toks = [_norm(t) for t in phrase.split() if _norm(t)]
        if not toks: raise StoryboardError(f"empty say: {phrase!r}")
        for i, (s, e, w) in enumerate(self.words):
            if self.M(s) < after: continue
            if toks[0] in w or w in toks[0] and len(w) > 2:
                if all(i + j < len(self.words) and (toks[j] in self.words[i + j][2] or self.words[i + j][2] in toks[j]) for j in range(len(toks))):
                    return s, self.words[min(len(self.words) - 1, i + len(toks) - 1)][1]
        earlier = [round(s, 1) for s, e, w in self.words if toks[0] in w and self.M(s) < after]
        if earlier: raise StoryboardError(f"the words {phrase!r} are said at source {earlier[:3]}s, which is BEFORE this beat starts (cut-timeline {after:.1f}s). Move the beat earlier or use `at:` in seconds")
        raise StoryboardError(f"could not find the words {phrase!r} in the transcript. Use `at:` in seconds, or fix the spelling to match transcript.json")
    def t(self, spec, key, default=None, after=0.0):
        if key in spec: return self.M(float(spec[key]))
        say = {"at": "say", "until": "until_say"}.get(key)
        if say and say in spec:
            s, e = self.find(spec[say], after); return self.M(s if key == "at" else e)
        if key == "until" and "for" in spec: return None
        return default

class Faces:
    """Face boxes over time (from the final presenter video). Graphics are placed so that they never overlap a face; if a beat cannot avoid one, compose stops with a clear message."""
    def __init__(self, track, cw, ch):
        self.fr = [dict(f) for f in track["frames"]] if track else []; self.step = track["step"] if track else 0.5; self.ratio = track["found_ratio"] if track else 0
        ws = sorted(max(b[2] for b in f["boxes"]) for f in self.fr if f["boxes"])
        mw = ws[len(ws) // 2] if ws else 0
        for f in self.fr: f["boxes"] = [b for b in f["boxes"] if b[2] >= 0.5 * mw]        # drop small false detections (clothing patterns, posters)
    def overlaps(self, rect, a, b, pad=12):
        x, y, w, h = rect; hits = []
        for f in self.fr:
            if f["t"] < a - self.step or f["t"] > b + self.step: continue
            for fx, fy, fw, fh in f["boxes"]:
                if min(x + w, fx + fw + pad) - max(x, fx - pad) > 0 and min(y + h, fy + fh + pad) - max(y, fy - pad) > 0: hits.append(f["t"])
        return sorted(set(hits))

class Builder:
    def __init__(self, dur, fps, assets_dir):
        self.dur, self.fps, self.assets = dur, fps, assets_dir; self.faces = Faces(None, 1080, 1920); self.scene_mode = False; self.html, self.js, self.events, self.rects = [], [], [], []; self.n = 0
    def uid(self, p="b"): self.n += 1; return f"{p}{self.n}"
    def ev(self, kind, t, **k): self.events.append(dict(kind=kind, t=round(float(t), 3), **k))
    def rect(self, x, y, w, h, a, b, full=False): self.rects.append(dict(x=x, y=y, w=w, h=h, t0=round(a, 3), t1=round(b, 3), full=full))
    def js_add(self, line): self.js.append(line)
    def enter_exit(self, eid, a, b, dy=60, scale=.965, blur=12, exit_y=30):
        self.js_add(f'tl.fromTo("#{eid}", {{opacity:0, y:{dy}, scale:{scale}, filter:"blur({blur}px)"}}, {{opacity:1, y:0, scale:1, filter:"blur(0px)", duration:.55, ease:"expo.out"}}, {a:.3f});')
        self.js_add(f'tl.fromTo("#{eid} .shim", {{x:-300, skewX:-18}}, {{x:1500, skewX:-18, duration:.9, ease:"power2.inOut"}}, {a + 0.25:.3f});')
        self.js_add(f'tl.fromTo("#{eid} .fic, #{eid} .dot", {{scale:.4, rotation:-14}}, {{scale:1, rotation:0, duration:.7, ease:"back.out(2.6)"}}, {a + 0.08:.3f});')
        self.js_add(f'tl.fromTo("#{eid} .ft, #{eid} .hdr", {{x:-28, opacity:0}}, {{x:0, opacity:1, duration:.5, ease:"power3.out"}}, {a + 0.16:.3f});')
        self.js_add(f'tl.fromTo("#{eid} .fs", {{x:-28, opacity:0}}, {{x:0, opacity:1, duration:.5, ease:"power3.out"}}, {a + 0.27:.3f});')
        self.js_add(f'tl.to("#{eid}", {{opacity:0, y:{exit_y}, filter:"blur(8px)", duration:.3, ease:"power3.in"}}, {max(a, b - 0.3):.3f});')
        self.js_add(f'tl.set("#{eid}", {{opacity:0}}, {b:.3f});')

def _check_icon(ik):
    if ik not in ICON: raise StoryboardError(f"unknown icon {ik!r}; available: {', '.join(sorted(ICON))}")
    return ICON[ik]

def _span(B, R, spec, default_len=2.5, after=0.0):
    a = R.t(spec, "at", after=after)
    if a is None: raise StoryboardError(f"beat needs `at:` (seconds in the source video) or `say:` (words from the transcript): {spec}")
    b = R.t(spec, "until", after=after)
    if b is None: b = a + float(spec.get("for", default_len))
    a = max(0.0, a); b = min(B.dur, b)
    if b - a < 0.4: raise StoryboardError(f"beat is shorter than 0.4 s after clamping to the video: {spec}")
    return a, b

def beat_card(B, R, s):
    a, b = _span(B, R, s); eid = B.uid(); color = s.get("color", ACCENT)
    slots = [int(s["y"])] if "y" in s else ([1340, 1270, 1200, 1130, 1072] if B.scene_mode else [1072, 1130, 1200, 1270, 1340])
    y = next((c_ for c_ in slots if not B.faces.overlaps((60, c_, 960, 164), a, b)), None)
    if y is None: raise StoryboardError(f"card {s.get('title')!r} at {a:.1f}-{b:.1f}s would cover a face in every position; use a `broll` beat for this moment or move it")
    B.html.append(f'<div id="{eid}" class="fcard glass" style="top:{y}px"><div class="fic" style="background:{color}">{_check_icon(s.get("icon", "star"))}</div><div class="shim"></div><div class="ftx"><div class="ft">{s["title"]}</div><div class="fs">{s.get("sub", "")}</div></div></div>')
    B.enter_exit(eid, a, b, dy=50); B.ev("card", a, hook=bool(s.get("hook"))); B.rect(60, y, 960, 164, a, b)

def beat_broll(B, R, s):
    a, b = _span(B, R, s, 3.0); eid = B.uid(); f = s["file"]; pos = s.get("pos", "50%")
    if not os.path.exists(os.path.join(B.assets, f)): raise StoryboardError(f"B-roll file not found in assets/: {f}")
    color = s.get("color", ACCENT)
    chip = f'<div class="chipl glass" style="top:196px;left:36px"><div class="dot" style="background:{color}">{_check_icon(s.get("icon", "play"))}</div><span>{s.get("label", "")}</span></div>' if s.get("label") else ""
    title = f'<div class="fst"><div class="fstt">{s["title"]}</div><div class="fsts">{s.get("sub", "")}</div></div>' if s.get("title") else ""
    B.html.append(f'<div id="{eid}" class="fsb" style="--pos:{pos} 50%"><video id="{eid}-v" class="clip" src="assets/{f}" muted playsinline data-start="{a:.3f}" data-duration="{b - a:.3f}" data-track-index="2"></video><div class="fshade"></div>{chip}{title}</div>')
    B.js_add(f'tl.fromTo("#{eid}", {{opacity:0, scale:1.05, filter:"blur(10px)"}}, {{opacity:1, scale:1, filter:"blur(0px)", duration:.38, ease:"expo.out"}}, {a:.3f});')
    B.js_add(f'tl.fromTo("#{eid}-v", {{scale:1.0}}, {{scale:1.12, duration:{b - a:.3f}, ease:"none"}}, {a:.3f});')
    B.js_add(f'tl.fromTo("#{eid} .fst", {{opacity:0, y:40}}, {{opacity:1, y:0, duration:.5, ease:"expo.out"}}, {a + .35:.3f});')
    B.js_add(f'tl.to("#{eid}", {{opacity:0, duration:.25, ease:"power2.in"}}, {max(a, b - .25):.3f});'); B.js_add(f'tl.set("#{eid}", {{opacity:0}}, {b:.3f});')
    B.ev("broll", a); B.rect(0, 0, 1080, 1920, a, b, full=True)

def beat_still(B, R, s):
    a, b = _span(B, R, s, 3.0); eid = B.uid(); icon = _check_icon(s.get("icon", "stetho")).replace("<svg ", '<svg style="width:560px;height:560px" ')
    c1, c2 = s.get("bg", ["#1d3b66", "#050b17"]); color = s.get("color", ACCENT)
    chip = f'<div class="chipl glass" style="top:196px;left:36px"><div class="dot" style="background:{color}">{_check_icon(s.get("chip_icon", s.get("icon", "stetho")))}</div><span>{s.get("label", "")}</span></div>' if s.get("label") else ""
    B.html.append(f'<div id="{eid}" class="fsb" style="background:radial-gradient(120% 80% at 50% 30%,{c1} 0%,{c2} 100%)"><div id="{eid}-ic" style="position:absolute;left:260px;top:330px">{icon}</div>{chip}'
                  f'<div class="fst"><div class="fstt">{s.get("title", "")}</div><div class="fsts">{s.get("sub", "")}</div></div></div>')
    B.js_add(f'tl.fromTo("#{eid}", {{opacity:0, scale:1.05, filter:"blur(10px)"}}, {{opacity:1, scale:1, filter:"blur(0px)", duration:.38, ease:"expo.out"}}, {a:.3f});')
    B.js_add(f'tl.fromTo("#{eid}-ic", {{scale:.92, y:20}}, {{scale:1.08, y:-10, duration:{b - a:.3f}, ease:"none"}}, {a:.3f});')
    B.js_add(f'tl.fromTo("#{eid} .fst", {{opacity:0, y:40}}, {{opacity:1, y:0, duration:.5, ease:"expo.out"}}, {a + .35:.3f});')
    B.js_add(f'tl.to("#{eid}", {{opacity:0, duration:.25, ease:"power2.in"}}, {max(a, b - .25):.3f});'); B.js_add(f'tl.set("#{eid}", {{opacity:0}}, {b:.3f});')
    B.ev("broll", a); B.rect(0, 0, 1080, 1920, a, b, full=True)

PANEL_OPTIONS = [(1056, 1.0), (1096, 0.9), (1136, 0.8), (1176, 0.72)]     # (top, scale): panels shrink a little instead of covering a chin

def _prect(y, sc): return (int(36 + 1008 * (1 - sc) / 2), y, int(1008 * sc), int(448 * sc))

def _panel_place(B, a, b, what, spec=None):
    if B.scene_mode and not (spec or {}).get("force"):
        raise StoryboardError(f"{what} at {a:.1f}-{b:.1f}s: this looks like a scene/vlog video (few faces), and a {what} panel covers about a quarter of the picture. Use a `card` or `broll` beat, or add `force: true` to accept it")
    for y, sc in PANEL_OPTIONS:
        if not B.faces.overlaps(_prect(y, sc), a, b): return y, sc
    hit = B.faces.overlaps(_prect(*PANEL_OPTIONS[-1]), a, b)
    raise StoryboardError(f"{what} at {a:.1f}-{b:.1f}s would cover a face (seen at t={hit[:4]}) even at the smallest size; use a `card` or `broll` beat here")

def _wrap(B, html, y, sc): B.html.append(f'<div class="pw" style="top:{y}px;transform:scale({sc})">{html}</div>')

def beat_checklist(B, R, s):
    items = s.get("items") or []
    if not 1 <= len(items) <= 5: raise StoryboardError("checklist needs 1-5 items (the card is 448 px tall)")
    a, b = _span(B, R, s, 8.0); y0, sc = _panel_place(B, a, b, "checklist", s); eid = B.uid(); warn = s.get("style", "check") == "warn"; ring = "#FF9F0A" if warn else (s.get("color") or ACCENT)
    tcol = s.get("title_color", "#FFB340" if warn else "#64D2FF"); ik = "warn" if warn else "check"; n = len(items); step = 66 if n >= 5 else (80 if n == 4 else 98); rows = ""
    for i, it in enumerate(items): rows += f'<div id="{eid}-r{i}" class="row" style="top:{104 + i * step}px"><div id="{eid}-b{i}" class="rb">{ICON[ik]}</div><div class="rt">{it["text"]}</div></div>'
    _wrap(B, f'<div id="{eid}" class="pcard glass"><div class="shim"></div><div class="hdr" style="color:{tcol}">{s["title"]}</div>{rows}</div>', y0, sc)
    B.enter_exit(eid, a, b, dy=110, scale=.94); B.ev("card", a); B.rect(*_prect(y0, sc), a, b)
    for i, it in enumerate(items):
        t = R.t(it, "at", default=a + 0.6 + 0.9 * i, after=a); t = min(max(t, a + 0.2), b - 0.3)
        B.js_add(f'tl.fromTo("#{eid}-r{i}", {{opacity:0, x:-30}}, {{opacity:1, x:0, duration:.4, ease:"power3.out"}}, {t - .05:.3f});')
        B.js_add(f'tl.to("#{eid}-b{i}", {{backgroundColor:"{ring}", borderColor:"{ring}", duration:.2, ease:"power2.out"}}, {t + .12:.3f});')
        B.js_add(f'tl.fromTo("#{eid}-b{i} svg", {{opacity:0, scale:.3}}, {{opacity:1, scale:1, duration:.32, ease:"back.out(2.2)"}}, {t + .12:.3f});')
        B.ev("warn" if warn else "tick", t)

def beat_tiles(B, R, s):
    a, b = _span(B, R, s, 4.0); y0, sc = _panel_place(B, a, b, "tiles", s); eid = B.uid(); html = f'<div id="{eid}" class="pcard" style="background:none;box-shadow:none">'
    for side, key in (("left:12px", "left"), ("right:12px", "right")):
        t = s[key]; c1 = t.get("color", ACCENT); c2 = t.get("color2", "#0B4FA8")
        ic = _check_icon(t.get("icon", "check")).replace("<svg ", '<svg style="width:130px;height:130px" ')
        html += f'<div id="{eid}-{key}" class="tile" style="{side};background:linear-gradient(160deg,{c1},{c2});box-shadow:0 20px 50px rgba(0,0,0,.3)">{ic}<div class="tt">{t["title"]}</div><div class="ts">{t.get("sub", "")}</div></div>'
    _wrap(B, html + "</div>", y0, sc)
    ta = R.t(s["left"], "at", default=a + .15, after=a); tb = R.t(s["right"], "at", default=a + .9, after=a)
    B.js_add(f'tl.fromTo("#{eid}", {{opacity:0, y:100}}, {{opacity:1, y:0, duration:.5, ease:"expo.out"}}, {a:.3f});')
    B.js_add(f'tl.fromTo("#{eid}-left", {{opacity:0, x:-120, scale:.9}}, {{opacity:1, x:0, scale:1, duration:.55, ease:"expo.out"}}, {ta:.3f});')
    B.js_add(f'tl.fromTo("#{eid}-right", {{opacity:0, x:120, scale:.9}}, {{opacity:1, x:0, scale:1, duration:.55, ease:"expo.out"}}, {tb:.3f});')
    B.js_add(f'tl.to("#{eid}", {{opacity:0, y:40, duration:.3, ease:"power3.in"}}, {max(a, b - .3):.3f});'); B.js_add(f'tl.set("#{eid}", {{opacity:0}}, {b:.3f});')
    B.ev("card", a); B.ev("vs_right", tb); B.rect(*_prect(y0, sc), a, b)

def beat_term(B, R, s):
    a, b = _span(B, R, s, 5.0); y0, sc = _panel_place(B, a, b, "term card", s); eid = B.uid(); chips = s.get("chips") or []
    html = (f'<div id="{eid}" class="pcard glass"><div style="position:absolute;left:44px;top:30px;font-weight:700;font-size:36px;color:rgba(235,235,245,.6)">{s.get("small", "")}</div>'
            f'<div id="{eid}-t" style="position:absolute;left:44px;top:92px;font-weight:900;font-size:{s.get("size", 92)}px;letter-spacing:-.03em;color:{s.get("color", "#FF9F0A")};white-space:nowrap">{s["term"]}</div>'
            f'<div style="position:absolute;left:44px;top:214px;font-weight:600;font-size:40px;color:rgba(235,235,245,.78)">{s.get("sub", "")}</div>')
    for i, c in enumerate(chips[:2]):
        pos = "left:44px" if i == 0 else "right:44px"; col = c.get("color", ACCENT)
        html += f'<div id="{eid}-c{i}" style="position:absolute;{pos};top:312px;height:88px;padding:0 34px;border-radius:44px;background:{col}33;border:2px solid {col};display:flex;align-items:center;font-weight:800;font-size:44px">{c["text"]}</div>'
    _wrap(B, html + "</div>", y0, sc); B.enter_exit(eid, a, b, dy=110, scale=.94)
    B.js_add(f'tl.fromTo("#{eid}-t", {{opacity:0, y:30, filter:"blur(10px)"}}, {{opacity:1, y:0, filter:"blur(0px)", duration:.6, ease:"expo.out"}}, {R.t(s, "term_at", default=a + .4, after=a):.3f});')
    for i, c in enumerate(chips[:2]):
        t = R.t(c, "at", default=a + 1.5 + i, after=a); B.js_add(f'tl.fromTo("#{eid}-c{i}", {{opacity:0, scale:.8}}, {{opacity:1, scale:1, duration:.5, ease:"back.out(2)"}}, {t:.3f});'); B.ev("tick", t)
    B.ev("card", a); B.rect(*_prect(y0, sc), a, b)

def beat_follow(B, R, s):
    a, b = _span(B, R, s, 5.0); y0, sc = _panel_place(B, a, b, "follow card", s); eid = B.uid(); ck = R.t(s, "click_at", default=a + (b - a) * 0.6, after=a)
    html = (f'<div id="{eid}" class="pcard glass" style="background:rgba(250,250,252,.96);border:1.5px solid rgba(0,0,0,.06)">'
            f'<div style="position:absolute;left:44px;top:26px;font-weight:800;font-size:46px;color:#1d1d1f">{s.get("heading", "Follow")}</div>'
            f'<div style="position:absolute;left:44px;top:92px;font-weight:600;font-size:32px;color:#86868b">{s.get("subheading", "")}</div>'
            f'<div style="position:absolute;left:36px;right:36px;top:168px;height:150px;border-radius:44px;background:#fff;border:2px solid rgba(0,0,0,.08);box-shadow:0 8px 30px rgba(0,0,0,.08);display:flex;align-items:center;gap:26px;padding:0 24px">'
            f'<div style="flex:none;width:100px;height:100px;border-radius:50px;background:linear-gradient(145deg,#FF9F0A,#FF375F);color:#fff;font-weight:900;font-size:50px;display:flex;align-items:center;justify-content:center">{s["name"][:1]}</div>'
            f'<div style="flex:1"><div style="font-weight:800;font-size:46px;color:#1d1d1f">{s["name"]}</div><div style="font-weight:600;font-size:30px;color:#86868b">{s.get("handle", "")}</div></div>'
            f'<div id="{eid}-btn" style="flex:none;height:84px;padding:0 44px;border-radius:42px;background:#0A84FF;color:#fff;font-weight:800;font-size:40px;display:flex;align-items:center;justify-content:center;min-width:220px"><span id="{eid}-bt">{s.get("button", "Follow")}</span></div></div>'
            f'<div id="{eid}-ty" style="position:absolute;left:0;right:0;top:340px;text-align:center;font-weight:900;font-size:56px;color:#1d1d1f;opacity:0">{s.get("thanks", "")}</div></div>')
    _wrap(B, html, y0, sc); B.enter_exit(eid, a, b - 0.03 if b >= B.dur - 0.1 else b, dy=120, scale=.94)
    B.js_add(f'tl.to("#{eid}-btn", {{scale:.9, duration:.12, ease:"power2.in"}}, {ck:.3f});'); B.js_add(f'tl.to("#{eid}-btn", {{scale:1, backgroundColor:"#30D158", duration:.35, ease:"back.out(3)"}}, {ck + .12:.3f});')
    B.js_add(f'tl.call(() => {{ document.getElementById("{eid}-bt").textContent = {json.dumps(s.get("done_text", "Following ✓"))}; }}, [], {ck + .1:.3f});')
    B.js_add(f'tl.fromTo("#{eid}-ty", {{opacity:0, y:24}}, {{opacity:1, y:0, duration:.5, ease:"expo.out"}}, {ck + .45:.3f});')
    B.ev("cta", a); B.ev("send", ck); B.rect(*_prect(y0, sc), a, b)

BUILDERS = dict(card=beat_card, broll=beat_broll, still=beat_still, checklist=beat_checklist, tiles=beat_tiles, term=beat_term, follow=beat_follow)

def load_storyboard(path):
    if not path: return []
    sb = yaml.safe_load(open(path)) or {}
    beats = sb.get("beats", sb) if isinstance(sb, dict) else sb
    if not isinstance(beats, list): raise StoryboardError("storyboard must be a list of beats (or have a `beats:` list)")
    for i, b in enumerate(beats):
        if not isinstance(b, dict) or b.get("type") not in BEAT_TYPES: raise StoryboardError(f"beat {i}: `type` must be one of {BEAT_TYPES}")
    return beats

def write_project(cfg, work, meta, timeline, transcript, groups, project):
    """Writes index.html + compositions into `project` and returns schedule {events, rects, seams}."""
    dur = round(timeline["duration"], 2); fps = meta["fps"]; M = mapper(timeline); R = Resolver(transcript, M, dur)
    cw, ch = meta["canvas"]; assets = os.path.join(project, "assets"); os.makedirs(os.path.join(project, "compositions"), exist_ok=True)
    from .picture import face_track
    B = Builder(dur, fps, assets); track = face_track(work, meta); B.faces = Faces(track, cw, ch); B.scene_mode = track["found_ratio"] < 0.4   # few faces = a scene/vlog, not a talking head
    if B.scene_mode: log("compose: few faces found - treating this as a scene video: cards go to the lower area and panels are only allowed where no face is present")
    beats = load_storyboard(cfg["graphics"].get("storyboard"))
    if (cw, ch) != (1080, 1920) and any(b["type"] not in ("broll", "still") for b in beats):
        log("compose: landscape canvas supports only `broll` and `still` beats; other beats are skipped"); beats = [b for b in beats if b["type"] in ("broll", "still")]
    for b in sorted(beats, key=lambda x: R.t(x, "at", default=0) or 0):
        try: BUILDERS[b["type"]](B, R, b)
        except KeyError as e: raise StoryboardError(f"beat {b.get('type')} is missing field {e}: {b}")
    full = [r for r in B.rects if r["full"]]
    for i, r in enumerate(full):                                    # two full-screen beats may not overlap in time
        for r2 in full[i + 1:]:
            if r["t0"] < r2["t1"] and r2["t0"] < r["t1"]: raise StoryboardError(f"two full-screen beats overlap around {r['t0']}s")
    gr = f'''<template>
  <style>{CSS}</style>
  <div id="root" data-composition-id="graphics" data-width="{cw}" data-height="{ch}">
    {chr(10).join(B.html)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join(B.js)}
    window.__timelines["graphics"] = tl;
  </script>
</template>
'''
    open(os.path.join(project, "compositions", "graphics.html"), "w").write(gr)
    # captions
    gh, cjs = "", []
    for k, g in enumerate(groups):
        gh += f'<div id="cg{k}" class="cg" data-text="{" ".join(g["words"])}">' + "".join(f'<span id="cw{k}_{j}" class="cw">{w}</span>' for j, w in enumerate(g["words"])) + "</div>\n"
        cjs.append(f'tl.fromTo("#cg{k}", {{opacity:0, y:14, filter:"blur(6px)"}}, {{opacity:1, y:0, filter:"blur(0px)", duration:.16, ease:"power3.out"}}, {g["t0"]});')
        for j, st in enumerate(g["st"]): cjs.append(f'tl.fromTo("#cw{k}_{j}", {{color:"rgba(255,255,255,.52)"}}, {{color:"rgba(255,255,255,1)", duration:.1, ease:"none"}}, {round(max(g["t0"], st - .02), 3)});')
        cjs.append(f'tl.to("#cg{k}", {{opacity:0, duration:.1, ease:"power2.in"}}, {round(max(g["t0"], g["t1"] - .1), 3)});'); cjs.append(f'tl.set("#cg{k}", {{opacity:0, visibility:"hidden"}}, {g["t1"]});')
    ctop = 1530 if ch >= cw else int(ch * 0.80)
    cap = f'''<template>
  <style>
    @font-face {{ font-family: 'Deva'; src: url('assets/fonts/NotoSansDevanagari-800.woff2') format('woff2'); font-weight: 100 900; unicode-range: U+0900-097F, U+200C-200D, U+25CC; }}
    #root {{ position: absolute; inset: 0; font-family: 'Inter', 'Deva', sans-serif; }}
    #cap-pill {{ position: absolute; left: {(cw - 864) // 2}px; width: 864px; top: {ctop}px; height: 90px; border-radius: 45px; background: rgba(20,20,22,.80); backdrop-filter: blur(26px) saturate(160%); border: 1.5px solid rgba(255,255,255,.14); box-shadow: 0 14px 40px rgba(0,0,0,.28); }}
    .cg {{ position: absolute; left: {(cw - 864) // 2}px; width: 864px; top: {ctop}px; height: 90px; display: flex; align-items: center; justify-content: center; white-space: nowrap; font-weight: 700; font-size: 52px; opacity: 0; color: #fff; }}
    .cw {{ display: inline-block; margin: 0 .16em; }}
  </style>
  <div id="root" data-composition-id="captions" data-width="{cw}" data-height="{ch}">
    <div id="cap-pill"></div>
    {gh}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    document.fonts.ready.then(() => {{
      document.querySelectorAll(".cg").forEach((el) => {{
        const r = window.__hyperframes.fitTextFontSize(el.dataset.text, {{ fontFamily: "Inter", fontWeight: 700, maxWidth: 790 }});
        el.style.fontSize = Math.min(54, r.fontSize) + "px";
      }});
      {chr(10).join("      " + l for l in cjs)}
      tl.fromTo("#cap-pill", {{opacity:0}}, {{opacity:1, duration:.3, ease:"power2.out"}}, 0.05);
      window.__timelines["captions"] = tl;
    }});
  </script>
</template>
'''
    open(os.path.join(project, "compositions", "captions.html"), "w").write(cap if cfg["captions"]["enabled"] else cap.replace(gh, ""))
    gcfg = cfg["graphics"]
    ui = f'''<template>
  <style> #root {{ position: absolute; inset: 0; }} #ui-track {{ position: absolute; left: 54px; top: 30px; width: {cw - 108}px; height: 8px; border-radius: 4px; background: rgba(0,0,0,.14); }}
  #ui-fill {{ position: absolute; left: 54px; top: 30px; width: {cw - 108}px; height: 8px; border-radius: 4px; background: {gcfg["accent"]}; transform-origin: 0 50%; }} </style>
  <div id="root" data-composition-id="ui" data-width="{cw}" data-height="{ch}"><div id="ui-track"></div><div id="ui-fill"></div></div>
  <script> const tl = gsap.timeline({{ paused: true }}); tl.fromTo("#ui-fill", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {dur}, ease: "none" }}, 0); window.__timelines["ui"] = tl; </script>
</template>
'''
    open(os.path.join(project, "compositions", "ui.html"), "w").write(ui if gcfg["progress_bar"] else ui.replace('<div id="ui-track"></div><div id="ui-fill"></div>', ""))
    seams = []; a = 0.0
    for s_, e_ in timeline["keep"][:-1]: a += e_ - s_; seams.append(round(a, 3))
    zl = [1.0, 1.08, 1.03, 1.09, 1.05, 1.07, 1.02, 1.06]; zoom = ['tl.set("#pzoom", {scale:1.0}, 0);']
    for i, t in enumerate(seams):                                  # a small punch-in on every jump cut hides the cut
        z = zl[i % len(zl)]; zoom.append(f'tl.fromTo("#pzoom", {{scale:{round(z + .03, 3)}}}, {{scale:{z}, duration:.3, ease:"power3.out", immediateRender:false}}, {t});')
    has_mix = True                      # the mix stage always writes assets/mix.m4a before the render (render refuses to start without it)
    root = f'''<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width={cw}, height={ch}" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style> * {{ margin:0; padding:0; box-sizing:border-box; }} html, body {{ margin:0; width:{cw}px; height:{ch}px; overflow:hidden; background:{gcfg["background"]}; }}
 #bg {{ position:absolute; inset:0; background:{gcfg["background"]}; }} #pw {{ position:absolute; left:0; top:0; width:{cw}px; height:{ch}px; }}
 #pzoom {{ position:absolute; inset:0; transform-origin:50% 30%; }} #presenter {{ position:absolute; left:0; top:0; width:{cw}px; height:{ch}px; object-fit:cover; }}
 #fade {{ position:absolute; inset:0; background:{gcfg["background"]}; opacity:0; }}</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="{cw}" data-height="{ch}">
<div id="bg"></div>
<div id="pw" data-layout-allow-overflow><div id="pzoom" data-layout-allow-overflow><video id="presenter" class="clip" src="assets/presenter.mp4" muted playsinline data-start="0" data-duration="{dur}" data-track-index="0"></video></div></div>
<div id="graphics" data-composition-id="graphics" data-composition-src="compositions/graphics.html" data-start="0" data-duration="{dur}" data-track-index="3" data-track-kind="graphics" data-width="{cw}" data-height="{ch}"></div>
<div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{dur}" data-track-index="4" data-track-kind="captions" data-width="{cw}" data-height="{ch}"></div>
<div id="ui" data-composition-id="ui" data-composition-src="compositions/ui.html" data-start="0" data-duration="{dur}" data-track-index="5" data-track-kind="graphics" data-width="{cw}" data-height="{ch}"></div>
{('<audio id="mix" src="assets/mix.m4a" data-start="0" data-duration="' + str(dur) + '" data-volume="1"></audio>') if has_mix else ""}
<div id="fade"></div>
</div><script>const tl = gsap.timeline({{ paused: true }});
{chr(10).join(zoom)}
tl.fromTo("#fade", {{opacity:0}}, {{opacity:1, duration:.4, ease:"power2.in"}}, {round(dur - .42, 3)});
window.__timelines["main"] = tl;</script></body></html>
'''
    open(os.path.join(project, "index.html"), "w").write(root)
    for f in ("hyperframes.json", "meta.json", "package.json"):
        if not os.path.exists(os.path.join(project, f)): raise FileNotFoundError(f"{f} missing in the project: run `vek init-project` first")
    sched = dict(events=B.events, rects=B.rects, seams=seams, duration=dur, canvas=[cw, ch])
    json.dump(sched, open(os.path.join(work, "schedule.json"), "w")); log(f"compose: {len(beats)} beats, {len(groups)} caption groups, {len(B.events)} sound events")
    return sched

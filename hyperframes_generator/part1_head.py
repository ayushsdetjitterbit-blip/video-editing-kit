import os
KW = os.environ.get("KIT_WORK", os.getcwd())          # work folder (see README for the layout)
KP = os.environ.get("KIT_PROJECT", os.path.join(KW, "project"))   # HyperFrames project folder
KS = os.environ.get("KIT_SEG_PROJECT", KP + "_seg")
"""HyperFrames project generator, iPhone style. Face is NEVER covered: full-frame mode uses slim cards under the chin,
panel mode shrinks the presenter to the top and puts B-roll / lists / diagrams in the lower panel."""
import json, os
P = KP
S = KW
BG = "#B4AFA5"
keep = json.load(open(S + "/n1/timeline.json"))["keep"]
DUR = round(sum(e - s_ for s_, e in keep), 2)          # length of the cut video
seams, a_ = [], 0.0
for s_, e_ in keep[:-1]: a_ += e_ - s_; seams.append(round(a_, 3))

# =============================================================== shared CSS + icons
CSS = """
  @font-face { font-family: 'Deva'; src: url('assets/fonts/NotoSansDevanagari-800.woff2') format('woff2'); font-weight: 100 900; unicode-range: U+0900-097F, U+200C-200D, U+25CC; }
  #root { position: absolute; inset: 0; font-family: 'Inter', 'Deva', sans-serif; color: #fff; }
  .glass { background: rgba(28,28,30,.78); backdrop-filter: blur(30px) saturate(180%); border: 1.5px solid rgba(255,255,255,.16); box-shadow: 0 18px 50px rgba(0,0,0,.26); }
  .fcard { position: absolute; left: 60px; top: 1072px; width: 960px; height: 164px; border-radius: 46px; opacity: 0; display: flex; align-items: center; gap: 28px; padding: 0 32px; }
  .fic { flex: none; width: 104px; height: 104px; border-radius: 30px; display: flex; align-items: center; justify-content: center; }
  .shim { position: absolute; top: -20px; bottom: -20px; left: 0; width: 220px; background: linear-gradient(100deg, rgba(255,255,255,0) 0%, rgba(255,255,255,.22) 50%, rgba(255,255,255,0) 100%); pointer-events: none; }
  .fcard, .pcard { overflow: hidden; }
  .fic svg { width: 60px; height: 60px; }
  .ftx { flex: 1 1 auto; min-width: 0; }
  .ft { font-weight: 800; font-size: 54px; line-height: 1.08; letter-spacing: -0.02em; white-space: nowrap; }
  .fs { font-weight: 600; font-size: 33px; line-height: 1.2; margin-top: 6px; color: rgba(235,235,245,.66); white-space: nowrap; }
  .pcard { position: absolute; left: 36px; top: 1056px; width: 1008px; height: 448px; border-radius: 48px; overflow: hidden; opacity: 0; }
  .pcard.glass { background: rgba(22,22,24,.94); }
  .pcard video { position: absolute; left: 0; top: 0; width: 1008px; height: 448px; object-fit: cover; }
  .fsb { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; opacity: 0; overflow: hidden; background: #111; }
  .fsb video { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; object-position: var(--pos, 50% 50%); }
  .fshade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,.30) 0%, rgba(0,0,0,0) 22%, rgba(0,0,0,0) 48%, rgba(0,0,0,.62) 100%); }
  .fst { position: absolute; left: 48px; right: 48px; top: 1210px; }
  .fstt { font-weight: 900; font-size: 84px; letter-spacing: -0.03em; line-height: 1.04; text-shadow: 0 4px 30px rgba(0,0,0,.45); }
  .fsts { font-weight: 700; font-size: 40px; margin-top: 10px; color: rgba(255,255,255,.9); text-shadow: 0 2px 16px rgba(0,0,0,.5); }
  .shade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,.22) 0%, rgba(0,0,0,0) 30%, rgba(0,0,0,0) 55%, rgba(0,0,0,.42) 100%); }
  .chipl { position: absolute; left: 22px; top: 22px; height: 70px; padding: 0 28px 0 14px; border-radius: 35px; display: flex; align-items: center; gap: 14px; font-weight: 800; font-size: 34px; letter-spacing: -0.01em; white-space: nowrap; }
  .chipl .dot { width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
  .chipl .dot svg { width: 28px; height: 28px; }
  .hdr { position: absolute; left: 44px; top: 22px; font-weight: 800; font-size: 54px; letter-spacing: -0.02em; }
  .cnt { position: absolute; right: 44px; top: 36px; font-weight: 700; font-size: 40px; color: rgba(235,235,245,.5); }
  .row { position: absolute; left: 44px; right: 44px; height: 64px; display: flex; align-items: center; gap: 26px; opacity: 0; }
  .rb { flex: none; width: 48px; height: 48px; border-radius: 50%; border: 4px solid rgba(235,235,245,.38); display: flex; align-items: center; justify-content: center; }
  .rb svg { width: 28px; height: 28px; opacity: 0; }
  .rt { font-weight: 700; font-size: 42px; letter-spacing: -0.01em; white-space: nowrap; }
  .tile { position: absolute; top: 24px; width: 470px; height: 400px; border-radius: 42px; opacity: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
  .tile .tt { font-weight: 900; font-size: 64px; letter-spacing: -0.02em; margin-top: 10px; }
  .tile .ts { font-weight: 600; font-size: 32px; margin-top: 8px; color: rgba(255,255,255,.82); }
  .dosha { position: absolute; top: 96px; width: 296px; height: 328px; border-radius: 38px; opacity: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; background: rgba(255,255,255,.07); border: 2px solid rgba(255,255,255,.14); }
  .dosha svg { width: 120px; height: 120px; }
  .dosha .dn { font-weight: 900; font-size: 50px; margin-top: 12px; }
  .dosha .de { font-weight: 600; font-size: 30px; line-height: 1.28; color: rgba(235,235,245,.66); margin-top: 6px; }
"""
def SV(body, sw=2.6, fill="none"): return f'<svg viewBox="0 0 24 24" fill="{fill}" stroke="#fff" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
ICON = {
  "drop": SV('<path d="M12 2.8c3.5 4.4 6 7.2 6 10.6a6 6 0 0 1-12 0c0-3.4 2.5-6.2 6-10.6z" fill="#fff" stroke="none"/>'),
  "check": SV('<path d="M5 12.8l4.6 4.6L19 7.6"/>', 3.2),
  "warn": SV('<path d="M12 3.4L21.8 20.4H2.2z" fill="#fff" stroke="none"/><path d="M12 9.4v5" stroke="#FF453A" stroke-width="2.6"/><circle cx="12" cy="17.2" r="1.3" fill="#FF453A" stroke="none"/>'),
  "leaf": SV('<path d="M5 19.5C5 10 10.5 4.5 20 4.5c0 9.5-5.5 15-14 15z" fill="#fff" stroke="none"/><path d="M5 19.5L13 11.5" stroke="#34C759" stroke-width="2"/>'),
  "user": SV('<circle cx="12" cy="8" r="4" fill="#fff" stroke="none"/><path d="M4.5 20.5c.8-4 3.7-6 7.5-6s6.7 2 7.5 6z" fill="#fff" stroke="none"/>'),
  "shield": SV('<path d="M12 2.8l7.5 2.8v6c0 4.8-3.2 8.3-7.5 9.7-4.3-1.4-7.5-4.9-7.5-9.7v-6z" fill="#fff" stroke="none"/><path d="M8.5 12.2l2.4 2.4 4.6-4.8" stroke="#0A84FF" stroke-width="2.6"/>'),
  "bulb": SV('<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V16h5v-.1c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z"/>', 2.2),
  "cal": SV('<rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M3.5 10h17M8 3v4M16 3v4"/>'),
  "heart": SV('<path d="M12 20.5s-7.5-4.6-7.5-10A4.3 4.3 0 0 1 12 7.8a4.3 4.3 0 0 1 7.5 2.7c0 5.4-7.5 10-7.5 10z" fill="#fff" stroke="none"/>'),
  "lab": SV('<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3"/>', 2.2),
  "doc": SV('<rect x="5" y="3.5" width="14" height="17" rx="3"/><path d="M8.5 9h7M8.5 13h7M8.5 17h4"/>', 2.2),
  "pill": SV('<rect x="2.8" y="8.5" width="18.4" height="7" rx="3.5" transform="rotate(-40 12 12)"/><path d="M9.2 14.8l5.6-5.6"/>', 2.2),
  "stetho": SV('<path d="M6 3v6a4 4 0 0 0 8 0V3M10 13v2a4 4 0 0 0 8 0v-1"/><circle cx="18" cy="12" r="2"/>', 2.2),
  "calend": SV('<rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M3.5 10h17M8 3v4M16 3v4"/>', 2.4),
  "bubble": SV('<path d="M4 5.5h16v11H11.5L7 20v-3.5H4z" fill="#fff" stroke="none"/>'),
  "wave": SV('<path d="M3 12c2-4 4-4 6 0s4 4 6 0 4-4 6 0"/>', 2.6),
}
def icon_sq(kind, color, size=104): return f'<div class="fic" style="background:{color}">{ICON[kind]}</div>'

class Scene:
    def __init__(s, sid, t0, t1): s.id, s.t0, s.t1, s.html, s.js = sid, t0, t1, [], []
    def L(s, t): return round(t - s.t0, 3)
    def enter_exit(s, eid, a, b, dy=60, scale=.965, blur=12, exit_y=30):
        s.js.append(f'tl.fromTo("#{eid}", {{opacity:0, y:{dy}, scale:{scale}, filter:"blur({blur}px)"}}, {{opacity:1, y:0, scale:1, filter:"blur(0px)", duration:.55, ease:"expo.out"}}, {s.L(a)});')
        s.js.append(f'tl.fromTo("#{eid} .shim", {{x:-300, skewX:-18}}, {{x:1500, skewX:-18, duration:.9, ease:"power2.inOut"}}, {s.L(a+0.25)});')
        s.js.append(f'tl.fromTo("#{eid} .fic, #{eid} .dot", {{scale:.4, rotation:-14}}, {{scale:1, rotation:0, duration:.7, ease:"back.out(2.6)"}}, {s.L(a+0.08)});')
        s.js.append(f'tl.fromTo("#{eid} .ft, #{eid} .hdr", {{x:-28, opacity:0}}, {{x:0, opacity:1, duration:.5, ease:"power3.out"}}, {s.L(a+0.16)});')
        s.js.append(f'tl.fromTo("#{eid} .fs", {{x:-28, opacity:0}}, {{x:0, opacity:1, duration:.5, ease:"power3.out"}}, {s.L(a+0.27)});')
        s.js.append(f'tl.to("#{eid}", {{opacity:0, y:{exit_y}, filter:"blur(8px)", duration:.3, ease:"power3.in"}}, {s.L(b-0.3)});')
        s.js.append(f'tl.set("#{eid}", {{opacity:0}}, {s.L(b)});')
    def full_card(s, cid, a, b, ik, color, title, sub, lang=False):
        eid = f"{s.id}-{cid}"
        s.html.append(f'<div id="{eid}" class="fcard glass">{icon_sq(ik, color)}<div class="shim"></div><div class="ftx"><div class="ft">{title}</div><div class="fs">{sub}</div></div></div>')
        s.enter_exit(eid, a, b, dy=50)
    def broll(s, cid, a, b, file, label, ik, color, extra="", top=""):
        eid = f"{s.id}-{cid}"
        s.html.append(f'<div id="{eid}" class="pcard"><video id="{eid}-v" class="clip" style="object-position:{pos} 50%" src="assets/{file}" muted playsinline data-start="{s.L(a)}" data-duration="{round(b-a,3)}" data-track-index="2"></video>'
                      f'<div class="shade"></div><div class="shim"></div><div class="chipl glass"><div class="dot" style="background:{color}">{ICON[ik]}</div><span>{label}</span></div>{extra}</div>')
        s.enter_exit(eid, a, b, dy=110, scale=.94)
        s.js.append(f'tl.fromTo("#{eid}-v", {{scale:1.0}}, {{scale:1.09, duration:{round(b-a,3)}, ease:"none"}}, {s.L(a)});')
    def fs(s, cid, a, b, file, label, ik, color, title="", sub="", pos="50%"):
        eid = f"{s.id}-{cid}"
        s.html.append(f'<div id="{eid}" class="fsb" style="--pos:{pos} 50%"><video id="{eid}-v" class="clip" src="assets/{file}" muted playsinline data-start="{s.L(a)}" data-duration="{round(b-a,3)}" data-track-index="2"></video>'
                      f'<div class="fshade"></div><div class="chipl glass" style="top:196px;left:36px"><div class="dot" style="background:{color}">{ICON[ik]}</div><span>{label}</span></div>'
                      + (f'<div class="fst"><div class="fstt">{title}</div><div class="fsts">{sub}</div></div>' if title else '') + '</div>')
        s.js.append(f'tl.fromTo("#{eid}", {{opacity:0, scale:1.05, filter:"blur(10px)"}}, {{opacity:1, scale:1, filter:"blur(0px)", duration:.38, ease:"expo.out"}}, {s.L(a)});')
        s.js.append(f'tl.fromTo("#{eid}-v", {{scale:1.0}}, {{scale:1.12, duration:{round(b-a,3)}, ease:"none"}}, {s.L(a)});')
        s.js.append(f'tl.fromTo("#{eid} .fst", {{opacity:0, y:40}}, {{opacity:1, y:0, duration:.5, ease:"expo.out"}}, {s.L(a+0.35)});')
        s.js.append(f'tl.to("#{eid}", {{opacity:0, duration:.25, ease:"power2.in"}}, {s.L(b-0.25)});')
        s.js.append(f'tl.set("#{eid}", {{opacity:0}}, {s.L(b)});')
    def checklist(s, cid, a, b, title, tcol, items, ik, ic_col, ring_col, count=True):
        eid = f"{s.id}-{cid}"; n = len(items); rows = ""
        step = 66 if n >= 5 else (80 if n == 4 else 98); y0 = 104
        for i, (t, txt) in enumerate(items):
            rows += (f'<div id="{eid}-r{i}" class="row" style="top:{y0 + i*step}px"><div id="{eid}-b{i}" class="rb" style="border-color:rgba(235,235,245,.38)">{ICON[ik]}</div><div class="rt">{txt}</div></div>')
        s.html.append(f'<div id="{eid}" class="pcard glass"><div class="shim"></div><div class="hdr" style="color:{tcol}">{title}</div>{rows}</div>')
        s.enter_exit(eid, a, b, dy=110, scale=.94)
        for i, (t, _) in enumerate(items):
            s.js.append(f'tl.fromTo("#{eid}-r{i}", {{opacity:0, x:-30}}, {{opacity:1, x:0, duration:.4, ease:"power3.out"}}, {s.L(t-0.05)});')
            s.js.append(f'tl.to("#{eid}-b{i}", {{backgroundColor:"{ring_col}", borderColor:"{ring_col}", duration:.2, ease:"power2.out"}}, {s.L(t+0.12)});')
            s.js.append(f'tl.fromTo("#{eid}-b{i} svg", {{opacity:0, scale:.3}}, {{opacity:1, scale:1, duration:.32, ease:"back.out(2.2)"}}, {s.L(t+0.12)});')
    def host(s):
        return (f'<div id="{s.id}" data-composition-id="{s.id}" data-composition-src="compositions/{s.id}.html" data-start="{s.t0}" data-duration="{round(s.t1-s.t0,3)}" '
                f'data-track-index="3" data-track-kind="graphics" data-width="1080" data-height="1920"></div>')
    def write(s):
        html = f'''<template>
  <style>{CSS}</style>
  <div id="root" data-composition-id="{s.id}" data-width="1080" data-height="1920">
    {chr(10).join(s.html)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join(s.js)}
    window.__timelines["{s.id}"] = tl;
  </script>
</template>
'''
        open(f"{P}/compositions/{s.id}.html", "w").write(html)

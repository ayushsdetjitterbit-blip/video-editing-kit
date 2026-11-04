import os
KW = os.environ.get("KIT_WORK", os.getcwd())          # work folder (see README for the layout)
KP = os.environ.get("KIT_PROJECT", os.path.join(KW, "project"))   # HyperFrames project folder
KS = os.environ.get("KIT_SEG_PROJECT", KP + "_seg")
import json, re
S0 = KW
P = KS
# time window of the scene to replace (clean-cut seconds): the "dont" scene is host start 80.15 s, 3.75 s long
T0, T1 = float(os.environ.get("SEG_T0", 80.15)), float(os.environ.get("SEG_T1", 83.90))
os.makedirs(KS + "/compositions", exist_ok=True)
for name in ("assets", "hyperframes.json", "meta.json", "package.json"):      # the segment project reuses the main project's assets
    dst = os.path.join(KS, name)
    if not os.path.lexists(dst) and os.path.exists(os.path.join(KP, name)): os.symlink(os.path.join(KP, name), dst)
D = round(T1 - T0, 3)
svg = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "seg_svg.txt")).read()
sched = json.load(open(S0 + "/v9/schedule.json"))
groups = []
for g in sched["groups"]:
    if g["t1"] <= T0 or g["t0"] >= T1: continue
    groups.append(dict(t0=round(max(0.0, g["t0"] - T0), 3), t1=round(min(D, g["t1"] - T0), 3), words=g["words"], st=[round(max(0.0, s - T0), 3) for s in g["st"]]))
# ---- captions (same look as the main video)
gh, cjs = "", []
for k, g in enumerate(groups):
    gh += f'<div id="cg{k}" class="cg" data-text="{" ".join(g["words"])}">' + "".join(f'<span id="cw{k}_{j}" class="cw">{w}</span>' for j, w in enumerate(g["words"])) + '</div>\n'
    cjs.append(f'tl.fromTo("#cg{k}", {{opacity:0, y:14, filter:"blur(6px)"}}, {{opacity:1, y:0, filter:"blur(0px)", duration:.16, ease:"power3.out"}}, {g["t0"]});')
    for j, st in enumerate(g["st"]):
        cjs.append(f'tl.fromTo("#cw{k}_{j}", {{color:"rgba(255,255,255,.52)"}}, {{color:"rgba(255,255,255,1)", duration:.1, ease:"none"}}, {round(max(g["t0"], st - 0.02), 3)});')
    cjs.append(f'tl.to("#cg{k}", {{opacity:0, duration:.1, ease:"power2.in"}}, {round(max(g["t0"], g["t1"] - 0.1), 3)});')
    cjs.append(f'tl.set("#cg{k}", {{opacity:0, visibility:"hidden"}}, {g["t1"]});')
src = open(KP + "/compositions/captions.html").read()
# keep the existing caption template, swap in this segment's groups
head = src[:src.index('<div id="cap-pill"></div>')]
cap = head + '<div id="cap-pill"></div>\n' + gh + '''  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
    document.fonts.ready.then(() => {
      document.querySelectorAll(".cg").forEach((el) => {
        const r = window.__hyperframes.fitTextFontSize(el.dataset.text, { fontFamily: "Inter", fontWeight: 700, maxWidth: 790 });
        el.style.fontSize = Math.min(54, r.fontSize) + "px";
      });
      ''' + "\n      ".join(cjs) + '''
      tl.set("#cap-pill", {opacity:1}, 0);
      window.__timelines["captions"] = tl;
    });
  </script>
</template>
'''
open(P + "/compositions/captions.html", "w").write(cap)
# ---- still-image scene replacing the talking-woman clip (same fades / chip / title as before)
still = f'''<template>
  <style>
  @font-face {{ font-family: 'Deva'; src: url('assets/fonts/NotoSansDevanagari-800.woff2') format('woff2'); font-weight: 100 900; unicode-range: U+0900-097F, U+200C-200D, U+25CC; }}
  #root {{ position: absolute; inset: 0; font-family: 'Inter', 'Deva', sans-serif; color: #fff; }}
  .glass {{ background: rgba(28,28,30,.78); backdrop-filter: blur(30px) saturate(180%); border: 1.5px solid rgba(255,255,255,.16); }}
  #st {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; opacity: 0; overflow: hidden; background: radial-gradient(120% 80% at 50% 30%, #1d3b66 0%, #0b1a33 60%, #050b17 100%); }}
  #st-ic {{ position: absolute; left: 260px; top: 330px; }}
  .chipl {{ position: absolute; left: 36px; top: 196px; height: 70px; padding: 0 28px 0 14px; border-radius: 35px; display: flex; align-items: center; gap: 14px; font-weight: 800; font-size: 34px; }}
  .chipl .dot {{ width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: #0A84FF; }}
  .chipl .dot svg {{ width: 28px; height: 28px; }}
  .fst {{ position: absolute; left: 48px; right: 48px; top: 1210px; }}
  .fstt {{ font-weight: 900; font-size: 84px; letter-spacing: -0.03em; line-height: 1.04; }}
  .fsts {{ font-weight: 700; font-size: 40px; margin-top: 10px; color: rgba(255,255,255,.9); }}
  </style>
  <div id="root" data-composition-id="dont" data-width="1080" data-height="1920">
    <div id="st"><div id="st-ic">{svg}</div>
      <div class="chipl glass"><div class="dot"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3v6a4 4 0 0 0 8 0V3M10 13v2a4 4 0 0 0 8 0v-1"/><circle cx="18" cy="12" r="2"/></svg></div><span>See a gynaecologist</span></div>
      <div class="fst"><div class="fstt">Don't ignore severe pain</div><div class="fsts">It is not always normal</div></div></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#st", {{opacity:0, scale:1.05, filter:"blur(10px)"}}, {{opacity:1, scale:1, filter:"blur(0px)", duration:.38, ease:"expo.out"}}, 0.05);
    tl.fromTo("#st-ic", {{scale:.92, y:20}}, {{scale:1.08, y:-10, duration:{D}, ease:"none"}}, 0.05);
    tl.fromTo("#st .fst", {{opacity:0, y:40}}, {{opacity:1, y:0, duration:.5, ease:"expo.out"}}, 0.4);
    tl.to("#st", {{opacity:0, duration:.25, ease:"power2.in"}}, {round(D - 0.25, 3)});
    window.__timelines["dont"] = tl;
  </script>
</template>
'''
open(P + "/compositions/dont.html", "w").write(still)
open(P + "/compositions/ui.html", "w").write(f'''<template>
  <style> #root {{ position: absolute; inset: 0; }} #ui-track {{ position: absolute; left: 54px; top: 30px; width: 972px; height: 8px; border-radius: 4px; background: rgba(0,0,0,.14); }}
  #ui-fill {{ position: absolute; left: 54px; top: 30px; width: {972 * T0 / 89.27:.2f}px; height: 8px; border-radius: 4px; background: #0A84FF; transform-origin: 0 50%; }} </style>
  <div id="root" data-composition-id="ui" data-width="1080" data-height="1920"><div id="ui-track"></div><div id="ui-fill"></div></div>
  <script> const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#ui-fill", {{ scaleX: 1 }}, {{ scaleX: {T1 / T0:.5f}, duration: {D}, ease: "none" }}, 0);
    window.__timelines["ui"] = tl; </script>
</template>
''')
# ---- root: presenter underneath (for the soft fades) + still scene + captions + progress
open(P + "/index.html", "w").write(f'''<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width=1080, height=1920" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style> * {{ margin:0; padding:0; box-sizing:border-box; }} html, body {{ margin:0; width:1080px; height:1920px; overflow:hidden; background:#B4AFA5; }}
 #pw {{ position:absolute; left:0; top:0; width:1080px; height:1920px; }} #pzoom {{ position:absolute; inset:0; transform-origin:50% 30%; }}
 #presenter {{ position:absolute; left:0; top:0; width:1080px; height:1920px; object-fit:cover; filter: brightness(.93) contrast(1.06) saturate(1.04); }}</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="{D}" data-width="1080" data-height="1920">
<div id="pw" data-layout-allow-overflow><div id="pzoom" data-layout-allow-overflow><video id="presenter" class="clip" src="assets/presenter.mp4" muted playsinline data-start="0" data-duration="{D}" data-media-start="{T0}" data-track-index="0"></video></div></div>
<div id="dont" data-composition-id="dont" data-composition-src="compositions/dont.html" data-start="0" data-duration="{D}" data-track-index="3" data-track-kind="graphics" data-width="1080" data-height="1920"></div>
<div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{D}" data-track-index="4" data-track-kind="captions" data-width="1080" data-height="1920"></div>
<div id="ui" data-composition-id="ui" data-composition-src="compositions/ui.html" data-start="0" data-duration="{D}" data-track-index="5" data-track-kind="graphics" data-width="1080" data-height="1920"></div>
</div><script>const tl = gsap.timeline({{ paused: true }}); tl.fromTo("#pzoom", {{scale:1.03}}, {{scale:1.0, duration:.3, ease:"power3.out", immediateRender:false}}, 0.05); window.__timelines["main"] = tl;</script></body></html>
''')
print("seg ok", D, len(groups), "caption groups")

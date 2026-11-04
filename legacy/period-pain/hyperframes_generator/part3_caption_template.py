cap = f'''<template>
  <style>
    @font-face {{ font-family: 'Deva'; src: url('assets/fonts/NotoSansDevanagari-800.woff2') format('woff2'); font-weight: 100 900; unicode-range: U+0900-097F, U+200C-200D, U+25CC; }}
    #root {{ position: absolute; inset: 0; font-family: 'Inter', 'Deva', sans-serif; }}
    #cap-pill {{ position: absolute; left: 108px; width: 864px; top: 1530px; height: 90px; border-radius: 45px; background: rgba(20,20,22,.80); backdrop-filter: blur(26px) saturate(160%);
                border: 1.5px solid rgba(255,255,255,.14); box-shadow: 0 14px 40px rgba(0,0,0,.28); }}
    .cg {{ position: absolute; left: 108px; width: 864px; top: 1530px; height: 90px; display: flex; align-items: center; justify-content: center; white-space: nowrap; font-weight: 700; font-size: 52px; opacity: 0; overflow: visible; }}
    .cw {{ display: inline-block; margin: 0 .16em; }}
  </style>
  <div id="root" data-composition-id="captions" data-width="1080" data-height="1920">
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
open(f"{P}/compositions/captions.html", "w").write(cap)
json.dump(dict(groups=groups, events=events, groups_panel=GROUPS, seams=seams), open(S + "/v9/schedule.json", "w"))

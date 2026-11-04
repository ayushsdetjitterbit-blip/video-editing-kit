# =============================================================== UI: progress bar (top, decorative)
ui = f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; }}
    #ui-track {{ position: absolute; left: 54px; top: 30px; width: 972px; height: 8px; border-radius: 4px; background: rgba(0,0,0,.14); }}
    #ui-fill {{ position: absolute; left: 54px; top: 30px; width: 972px; height: 8px; border-radius: 4px; background: #0A84FF; transform-origin: 0 50%; }}
  </style>
  <div id="root" data-composition-id="ui" data-width="1080" data-height="1920"><div id="ui-track"></div><div id="ui-fill"></div></div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#ui-fill", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {DUR}, ease: "none" }}, 0);
    window.__timelines["ui"] = tl;
  </script>
</template>
'''
open(f"{P}/compositions/ui.html", "w").write(ui)

# =============================================================== ROOT: presenter, mode switching, jump-cut masking
def in_panel(t): return any(a - 0.05 <= t <= b for a, b in GROUPS)
full_lv, panel_lv = [1.0, 1.08, 1.03, 1.09, 1.05, 1.07, 1.02, 1.06], [1.0, 1.035, 1.0, 1.045]
zoom = ['tl.set("#pzoom", {scale:1.0}, 0);']
fi = pi = 0
GROUPS = []
for t in seams:
    if in_panel(t): z = panel_lv[pi % len(panel_lv)]; pi += 1
    else: z = full_lv[fi % len(full_lv)]; fi += 1
    zoom.append(f'tl.fromTo("#pzoom", {{scale:{round(z + 0.03, 3)}}}, {{scale:{z}, duration:.3, ease:"power3.out", immediateRender:false}}, {t});')
mode = []
hosts = "\n      ".join(sc.host() for sc in scenes)
root = f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: {BG}; }}
      #bg {{ position: absolute; inset: 0; background: {BG}; }}
      #pw {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; transform-origin: 50% 0%; }}
      #pzoom {{ position: absolute; inset: 0; transform-origin: 50% 30%; }}
      #presenter {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; filter: brightness(.93) contrast(1.06) saturate(1.04); }}
      #stackfade {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; opacity: 0; background: linear-gradient(180deg, rgba(180,175,165,0) 0px, rgba(180,175,165,0) 790px, {BG} 842px, {BG} 100%); }}
      #sidefade {{ position: absolute; left: 0; top: 0; width: 1080px; height: 860px; opacity: 0; background: linear-gradient(90deg, {BG} 0px, {BG} 124px, rgba(180,175,165,0) 196px, rgba(180,175,165,0) 884px, {BG} 956px, {BG} 100%); }}
      #aur {{ position: absolute; left: 0; top: 1290px; width: 1080px; height: 630px; opacity: 0; overflow: hidden; }}
      #aur i {{ position: absolute; border-radius: 50%; filter: blur(90px); }}
      #fade {{ position: absolute; inset: 0; background: {BG}; opacity: 0; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-width="1080" data-height="1920">
      <div id="bg"></div>
      <div id="pw" data-layout-allow-overflow><div id="pzoom" data-layout-allow-overflow><video id="presenter" class="clip" src="assets/presenter.mp4" muted playsinline data-start="0" data-duration="{DUR}" data-track-index="0"></video></div></div>
      
      <div id="aur" style="display:none"><i id="ab1" style="left:-120px;top:120px;width:520px;height:420px;background:rgba(10,132,255,.20)"></i><i id="ab2" style="left:560px;top:260px;width:520px;height:420px;background:rgba(94,92,230,.17)"></i><i id="ab3" style="left:300px;top:-60px;width:420px;height:300px;background:rgba(48,209,88,.14)"></i></div>
      <div id="brandline" style="position:absolute;left:0;width:1080px;top:1690px;display:none;text-align:center;font-family:Inter,sans-serif;font-weight:700;font-size:32px;color:#2c2c2e;letter-spacing:.02em;opacity:0">Women's Health · Dr. Amrata Jain</div>
      {hosts}
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{DUR}" data-track-index="4" data-track-kind="captions" data-width="1080" data-height="1920"></div>
      <div id="ui" data-composition-id="ui" data-composition-src="compositions/ui.html" data-start="0" data-duration="{DUR}" data-track-index="5" data-track-kind="graphics" data-width="1080" data-height="1920"></div>
      {'<audio id="mix" src="assets/mix.m4a" data-start="0" data-duration="' + str(DUR) + '" data-volume="1"></audio>' if os.path.exists(P + "/assets/mix.m4a") else ""}
      <div id="fade"></div>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      {chr(10).join("      " + l for l in zoom)}
      {chr(10).join("      " + l for l in mode)}
      tl.fromTo("#ab1", {{x:0, y:0}}, {{x:200, y:-70, duration:{DUR}, ease:"sine.inOut"}}, 0);
      tl.fromTo("#ab2", {{x:0, y:0}}, {{x:-240, y:60, duration:{DUR}, ease:"sine.inOut"}}, 0);
      tl.fromTo("#ab3", {{x:0, y:0}}, {{x:160, y:90, duration:{DUR}, ease:"sine.inOut"}}, 0);
      tl.fromTo("#fade", {{opacity:0}}, {{opacity:1, duration:.4, ease:"power2.in"}}, {round(DUR - 0.42, 3)});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
'''
open(f"{P}/index.html", "w").write(root)
print("scenes", len(scenes), "panel groups", len(GROUPS), "caption groups", len(groups), "events", len(events))

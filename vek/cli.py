"""Command line:  python -m vek <command>
  init VIDEO          create a video folder with config.yaml and a storyboard template
  run CONFIG          run every stage (resumable; finished stages are skipped): ingest, transcribe, cut, voice, picture, compose, mix, render, qa
  draft CONFIG        print the transcript with timestamps and a suggested storyboard skeleton
  qa CONFIG VIDEO     run the quality gates on a rendered file
  doctor              check that the tools and models are available
"""
import argparse, json, os, shutil, sys, yaml
from . import config as C, ingest as I, transcribe as T, cut as K, voice as V, picture as P, captions as CA, compose as CO, mix as MX, render as R, qa as Q
from .util import Stage, fp, log, which, probe

STAGES = ["ingest", "transcribe", "cut", "voice", "picture", "compose", "mix", "render", "qa"]

def paths(cfg):
    work = cfg["workdir"]; return work, os.path.join(os.path.dirname(work), "project") if os.path.basename(work) == "work" else os.path.join(work, "project")

def run_pipeline(cfg_path, stages=None):
    cfg = C.load(cfg_path); work, project = paths(cfg); os.makedirs(work, exist_ok=True); S = Stage(work)
    want = stages or STAGES; meta_p = os.path.join(work, "meta.json")
    def need(name, *fps_): return name in want and not S.done(name, fp(*fps_))
    # ---- ingest
    if need("ingest", cfg["input"], cfg["fps"], cfg["canvas"]):
        meta = I.ingest(cfg, work); json.dump(meta, open(meta_p, "w")); S.mark("ingest", fp(cfg["input"], cfg["fps"], cfg["canvas"]))
    meta = json.load(open(meta_p))
    # ---- transcribe
    if need("transcribe", cfg["input"], cfg["language"], cfg["cut"]["pause_min"]):
        T.transcribe(work, cfg["language"], cfg["cut"]["pause_min"]); S.mark("transcribe", fp(cfg["input"], cfg["language"], cfg["cut"]["pause_min"]))
    tr = json.load(open(os.path.join(work, "transcript.json")))
    # ---- cut
    if need("cut", cfg["input"], cfg["cut"], tr["language"]):
        K.cut_stage(cfg, work, meta); S.mark("cut", fp(cfg["input"], cfg["cut"], tr["language"])); [S.clear(s) for s in ("voice", "picture", "compose", "mix", "render", "qa")]
    tl = json.load(open(os.path.join(work, "timeline.json")))
    # ---- voice
    if need("voice", os.path.join(work, "timeline.json"), cfg["voice"]):
        V.build_raw(work, meta["fps"]); V.enhance(work, cfg); S.mark("voice", fp(os.path.join(work, "timeline.json"), cfg["voice"]))
    # ---- picture
    pfp = fp(os.path.join(work, "timeline.json"), cfg["picture"], meta["canvas"])
    if need("picture", pfp):
        st = P.analyze(work, meta); pl = P.plan(cfg, st, meta); json.dump(pl, open(os.path.join(work, "picture_plan.json"), "w")); P.presenter(cfg, work, meta, st, pl); S.mark("picture", pfp)
    # ---- compose (cheap: always rebuild when asked, it depends on the storyboard)
    groups = None
    if "compose" in want or "mix" in want or "render" in want:
        M = CA.mapper(tl); kept = sorted({w for seg in tl["windows_per_segment"] for w in seg})
        chunks = CA.chunks_from_transcript(tr, tl, cfg, kept); groups = CA.apply_draft(CA.build_groups(chunks, M, round(tl["duration"], 2), meta["fps"]), work)
        CA.write_draft(work, groups)
        R.init_project(project, cfg["render"]["hyperframes_version"], work, os.path.join(os.path.dirname(os.path.abspath(cfg_path)), "assets")); R.link_presenter(work, project)
        sched = CO.write_project(cfg, work, meta, tl, tr, groups, project)
    # ---- mix
    if "mix" in want: MX.build(cfg, work, project, tl["duration"])
    # ---- render + qa
    out = os.path.join(os.path.dirname(work) if os.path.basename(work) == "work" else work, "final_HQ.mp4")
    if "render" in want:
        R.render(project, out, cfg, tl["duration"], meta["fps"])
    if "qa" in want and os.path.exists(out):
        rep = Q.run_qa(out, work, cfg, meta, tl); print("QA PASSED" if rep["passed"] else "QA FAILED - see qa_report.json"); return 0 if rep["passed"] else 2
    return 0

def init(video, name=None, lang="auto"):
    name = name or os.path.splitext(os.path.basename(video))[0].replace(" ", "_")[:40]; os.makedirs(os.path.join(name, "assets"), exist_ok=True)
    cfgp = os.path.join(name, "config.yaml")
    yaml.safe_dump({"input": os.path.abspath(video), "workdir": "work", "language": lang, "graphics": {"storyboard": "storyboard.yaml"}, "audio": {"music": None}},
                   open(cfgp, "w"), sort_keys=False)
    open(os.path.join(name, "storyboard.yaml"), "w").write(STORYBOARD_TEMPLATE)
    print(f"created {name}/  -> edit {cfgp} and {name}/storyboard.yaml, then:  python -m vek run {cfgp}")

STORYBOARD_TEMPLATE = """# Storyboard: the only part that is specific to this video. Times are SOURCE seconds (before cuts); use `say:` to anchor on spoken words instead.
# Beat types: card, broll, still, checklist, tiles, term, follow.   Run `python -m vek draft config.yaml` to see the transcript with times.
beats:
  - type: card              # lower-third card under the chin (never covers the face)
    at: 0.5
    until: 2.5
    icon: star              # see vek/compose.py ICON for the list
    color: "#0A84FF"
    title: "Your title"
    sub: "Your subtitle"
    hook: true              # adds the opening sound
#  - type: broll            # full-screen footage (hides the face on purpose) - put the file in assets/
#    file: clip.mp4
#    at: 12.0
#    until: 15.0
#    label: "Short label"
#    title: "Big title"
#    sub: "Smaller line"
#  - type: checklist
#    title: "Normal if"
#    at: 20
#    until: 28
#    items: [{at: 21, text: "Item one"}, {at: 23, text: "Item two"}]
#  - type: follow
#    name: "Your Name"
#    handle: "Your tagline"
#    heading: "Follow"
#    at: 80
#    until: 88
"""

def draft(cfg_path):
    cfg = C.load(cfg_path); work, _ = paths(cfg); tr = json.load(open(os.path.join(work, "transcript.json"))); tl = json.load(open(os.path.join(work, "timeline.json")))
    print(f"language: {tr['language']}   cut length: {tl['duration']:.1f}s   dropped: {[d['reason'] + ' #' + str(d['index']) for d in tl['dropped']]}\n")
    for i, w in enumerate(tr["windows"]): print(f"#{i:<3} {w['a']:7.2f}-{w['b']:7.2f}  {w['text']}")
    print("\nSuggested beats: a hook card at the first sentence, a CTA `follow` beat at the last sentences, and a `broll` or `checklist` beat for each list or key term.")

def doctor():
    ok = True
    for tool in ("ffmpeg", "ffprobe", "node", "npx"):
        p = which(tool); ok = ok and bool(p); print(f"{'OK ' if p else 'MISSING'} {tool} {p or ''}")
    for mod in ("numpy", "cv2", "scipy", "onnxruntime", "faster_whisper", "noisereduce", "yaml"):
        try: __import__(mod); print(f"OK  python: {mod}")
        except Exception as e: ok = False; print(f"MISSING python: {mod}  ({e})")
    print("models dir:", P.models_dir()); return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser(prog="vek"); sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("init"); a.add_argument("video"); a.add_argument("--name"); a.add_argument("--lang", default="auto")
    r = sub.add_parser("run"); r.add_argument("config"); r.add_argument("--stages", help="comma list, e.g. compose,mix,render,qa")
    d = sub.add_parser("draft"); d.add_argument("config")
    q = sub.add_parser("qa"); q.add_argument("config"); q.add_argument("video")
    sub.add_parser("doctor")
    n = ap.parse_args()
    if n.cmd == "init": init(n.video, n.name, n.lang)
    elif n.cmd == "run": sys.exit(run_pipeline(n.config, n.stages.split(",") if n.stages else None))
    elif n.cmd == "draft": draft(n.config)
    elif n.cmd == "doctor": sys.exit(doctor())
    elif n.cmd == "qa":
        cfg = C.load(n.config); work, _ = paths(cfg); meta = json.load(open(os.path.join(work, "meta.json"))); tl = json.load(open(os.path.join(work, "timeline.json")))
        rep = Q.run_qa(n.video, work, cfg, meta, tl); sys.exit(0 if rep["passed"] else 2)

if __name__ == "__main__":
    main()

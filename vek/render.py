"""HyperFrames project setup and render. The render is the slowest stage (about 15 s per second of video on 4 cores); it is skipped when nothing changed."""
import glob, os, shutil, subprocess
from .util import run, log

def init_project(project, hf_version, work, user_assets=None):
    """Scaffold once with the pinned HyperFrames version, then link/copy the files every project needs."""
    os.makedirs(project, exist_ok=True)
    if not all(os.path.exists(os.path.join(project, f)) for f in ("hyperframes.json", "meta.json", "package.json")):
        tmp = os.path.join(work, "scaffold_tmp"); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
        run(["npx", "--yes", f"hyperframes@{hf_version}", "init", "scaffold", "--example", "blank", "--resolution", "portrait", "--non-interactive", "--skip-skills"], cwd=tmp, timeout=900)
        for f in ("hyperframes.json", "meta.json", "package.json", "AGENTS.md", "CLAUDE.md"):
            src = os.path.join(tmp, "scaffold", f)
            if os.path.exists(src): shutil.copy(src, os.path.join(project, f))
        shutil.rmtree(tmp, ignore_errors=True)
    a = os.path.join(project, "assets"); os.makedirs(os.path.join(a, "fonts"), exist_ok=True)
    font = os.path.join(os.path.dirname(__file__), "assets", "fonts", "NotoSansDevanagari-800.woff2")
    if not os.path.exists(os.path.join(a, "fonts", "NotoSansDevanagari-800.woff2")): shutil.copy(font, os.path.join(a, "fonts"))
    if user_assets and os.path.isdir(user_assets):                      # B-roll and images the user put next to config.yaml
        for f in os.listdir(user_assets):
            dst = os.path.join(a, f)
            if os.path.lexists(dst): os.remove(dst)
            os.symlink(os.path.abspath(os.path.join(user_assets, f)), dst)

def link_presenter(work, project):
    dst = os.path.join(project, "assets", "presenter.mp4")
    if os.path.lexists(dst): os.remove(dst)
    os.symlink(os.path.abspath(os.path.join(work, "presenter.mp4")), dst)

def free_gb(path): return shutil.disk_usage(path).free / 1e9

def render(project, out, cfg, dur, fps):
    if not os.path.exists(os.path.join(project, "assets", "mix.m4a")): raise RuntimeError("assets/mix.m4a is missing: run the `mix` stage before `render`")
    need = 0.12 * dur * fps / 30 / 1.0                      # PNG frame cache: ~2 MB per frame at 1080x1920, plus the output
    need = dur * fps * 2.1e6 / 1e9 + 1
    if free_gb(project) < need: raise RuntimeError(f"not enough free disk for the render: need about {need:.1f} GB, have {free_gb(project):.1f} GB")
    shutil.rmtree("/tmp/hyperframes-extract-cache-0", ignore_errors=True)
    r = cfg["render"]; ver = r["hyperframes_version"]
    log(f"render: {dur:.1f}s at {fps} fps (about {dur * 12 / 60:.0f}-{dur * 15 / 60:.0f} min)")
    p = subprocess.run(["npx", "--yes", f"hyperframes@{ver}", "render", "--quality", r["quality"], "--crf", str(r["crf"]), "--video-frame-format", "png", "-o", os.path.abspath(out)],
                       cwd=project, capture_output=True, text=True)
    shutil.rmtree("/tmp/hyperframes-extract-cache-0", ignore_errors=True)
    if p.returncode != 0 or not os.path.exists(out): raise RuntimeError("render failed:\n" + (p.stdout + p.stderr)[-2500:])
    return out

def lint(project, ver):
    p = subprocess.run(["npx", "--yes", f"hyperframes@{ver}", "lint"], cwd=project, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)[-3000:]

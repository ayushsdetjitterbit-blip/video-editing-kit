"""Step 3: cut between phrases only (never inside one) and render clean_master.mp4 + timeline.json.
Needs src.mp4, tr2.json (from 02_transcribe_windows.py). Frame-exact: 30 fps, 1470 audio samples per frame at 44.1 kHz.
Edit START_OVERRIDE if a window starts with a breath / filler that you want trimmed (window index -> source seconds)."""
import json, subprocess
F = 30
START_OVERRIDE = {}        # e.g. {5: 29.97}
win = json.load(open("tr2.json"))
segs = []
for k, s in enumerate(win):
    a = START_OVERRIDE.get(k, s["a"]); b = s["b"]
    segs.append([a - 0.07, b + 0.10])                  # keep 70 ms before and 100 ms after every phrase
segs[0][0] = max(0, segs[0][0])
fr = lambda t: round(t * F)
keep = []
for a, b in segs:
    A, B = fr(a), fr(b)
    if keep and A <= keep[-1][1]: keep[-1][1] = max(B, keep[-1][1])
    else: keep.append([A, B])
tot = sum(b - a for a, b in keep) / F
print(len(keep), "segments, kept %.2f s" % tot)
json.dump(dict(keep=[[a / F, b / F] for a, b in keep], fr=keep), open("timeline.json", "w"))
v, a_ = [], []
for i, (A, B) in enumerate(keep):
    v.append(f"[0:v]trim=start_frame={A}:end_frame={B},setpts=PTS-STARTPTS[v{i}]")
    a_.append(f"[0:a]atrim=start_sample={A*1470}:end_sample={B*1470},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.006,afade=t=out:st={(B-A)/F-0.006:.4f}:d=0.006[a{i}]")
n = len(keep)
open("fc.txt", "w").write(";".join(v + a_) + ";" + "".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "src.mp4", "-filter_complex_script", "fc.txt", "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "256k", "clean_master.mp4"], check=True)

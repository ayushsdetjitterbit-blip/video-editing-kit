"""Step 1: find speech runs and pauses from the audio energy (writes runs.json).
Run in the work folder that contains a16.wav (16 kHz mono) made with:
  ffmpeg -i src.mp4 -vn -ac 1 -ar 16000 a16.wav
"""
import wave, numpy as np, json
w = wave.open("a16.wav"); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
hop = 160; n = len(x) // hop
db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-6)
thr = max(np.percentile(db, 10) + 8, -48)           # 10 ms frames, threshold = room noise + 8 dB
sp = db > thr
def runs(b):
    o, s = [], None
    for i, v in enumerate(b):
        if v and s is None: s = i
        if not v and s is not None: o.append([s, i]); s = None
    if s is not None: o.append([s, len(b)])
    return o
m = []
for a, b in runs(sp):
    if m and a - m[-1][1] < 8: m[-1][1] = b            # fill gaps shorter than 80 ms
    else: m.append([a, b])
S = [(a / 100, b / 100) for a, b in m if b - a >= 8]   # drop blips shorter than 80 ms
json.dump(S, open("runs.json", "w"))
for i in range(len(S) - 1):
    g = S[i + 1][0] - S[i][1]
    if g >= 0.25: print(f"pause {S[i][1]:.2f} -> {S[i+1][0]:.2f} = {g:.2f}s")

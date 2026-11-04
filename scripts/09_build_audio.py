import os
KW = os.environ.get("KIT_WORK", os.getcwd())          # work folder (see README for the layout)
KP = os.environ.get("KIT_PROJECT", os.path.join(KW, "project"))   # HyperFrames project folder
KS = os.environ.get("KIT_SEG_PROJECT", KP + "_seg")
"""Step 3 sound: enhanced voice (untouched character) + Mixkit music bed (EQ-carved, ducked) + SFX locked to the on-screen events."""
import json, wave, subprocess, numpy as np
S = KW; A = S + "/n1/audio"
DUR = round(sum(e - s_ for s_, e in json.load(open(S + "/n1/timeline.json"))["keep"]), 2) + 0.05
sched = json.load(open(S + "/v9/schedule.json")); EV = sched["events"]; SEAMS = sched["seams"]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_helpers.py")).read().split("# ---------- music bed")[0].replace("DUR = 35.34", f"DUR = {DUR}"))

from scipy.signal import fftconvolve
def reverb(x, rt=0.55, mix=0.25, seed=3):
    n = int(rt * 2 * SR); t = np.arange(n) / SR
    ir = np.random.default_rng(seed).standard_normal(n) * np.exp(-t / (rt / 3)); ir[0] = 0
    ir = np.stack([ir, np.roll(ir, 97)], axis=1)
    wet = np.stack([fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], axis=1)
    wet /= (np.abs(wet).max() + 1e-9) / (np.abs(x).max() + 1e-9)
    return x * (1 - mix) + wet * mix
def rd(p):
    w = wave.open(p); return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
# ---- voice ----
v = rd(A + "/voice_enh.wav"); ref = rd(A + "/voice_aligned_raw.wav")
def bpf(x):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < 300) | (f > 3000)] = 0; return np.fft.irfft(X, len(x))
n = min(len(v), len(ref), SR * 40); a, b = bpf(v[:n]), bpf(ref[:n]); Lc = 1 << int(np.ceil(np.log2(2 * n)))
cc = np.fft.irfft(np.fft.rfft(a, Lc) * np.conj(np.fft.rfft(b, Lc)), Lc); m = int(0.08 * SR); lags = np.r_[np.arange(0, m), np.arange(-m, 0)]; idx = np.r_[cc[:m], cc[-m:]]
lag = int(lags[idx.argmax()]); print("enhanced voice vs aligned original: lag %.1f ms" % (lag / SR * 1000))
if lag > 0: v = np.concatenate([v[lag:], np.zeros(lag)])           # remove any processing delay so lips and sound line up
elif lag < 0: v = np.concatenate([np.zeros(-lag), v[:lag]])
voice = np.zeros(N); voice[:min(N, len(v))] = v[:N]

# ---- music: Mixkit "Raising Me Higher" (Ahjay Stelino), Mixkit Stock Music Free License ----
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "0.3", "-t", str(DUR), "-i", S + "/v3/music/34.mp3", "-ac", "2", "-ar", str(SR),
                      "-af", "highpass=f=70,lowpass=f=12000,equalizer=f=2200:t=q:w=0.8:g=-3.5", "-f", "f32le", "-"], capture_output=True).stdout
mu = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
music = np.zeros((N, 2)); music[:min(N, len(mu))] = mu[:N]
music *= 0.058 / (np.sqrt(np.mean(music ** 2)) + 1e-9)
music *= (np.minimum(1, T / 1.2) * np.clip((DUR - T) / 2.6, 0, 1))[:, None]
win = int(0.06 * SR); e = np.sqrt(np.convolve(voice ** 2, np.ones(win) / win, mode="same"))
e = np.convolve(e, np.hanning(int(0.30 * SR)) / np.hanning(int(0.30 * SR)).sum(), mode="same")
duck = 1 - 0.62 * np.clip(e / (np.percentile(e, 90) + 1e-9), 0, 1)
music *= duck[:, None]

# ---- SFX ----
sfx = np.zeros((N, 2))
def click(t, g=-22):
    n_ = int(0.03 * SR); tt = np.arange(n_) / SR
    c = bp_noise(n_, lambda x: 3200, 0.5, int(t * 100) % 97) * np.exp(-tt / 0.006) + 0.6 * np.sin(2 * np.pi * 180 * tt) * np.exp(-tt / 0.008)
    add(sfx, c, t, db(g))
add(sfx, whoosh(0.45, 300, 3200, 5), 0.0, db(-18)); add(sfx, thump(55, 0.6, 0.18), 0.06, db(-14)); add(sfx, bell(midi(88), 0.9, 0.3), 0.12, db(-29))
for i, t in enumerate(SEAMS): add(sfx, whoosh(0.2, 600, 4200, 10 + i), t - 0.12, db(-33), pan=-0.4 if i % 2 else 0.4)      # jump-cut air
for k, ev in enumerate(EV):
    t, kd = ev["t"], ev["kind"]
    if kd == "panel": add(sfx, whoosh(0.5, 250, 2600, 40 + k), t - 0.12, db(-17), pan=0.0)                                 # presenter glides up
    elif kd == "panel_end" and t < 81: add(sfx, whoosh(0.42, 2400, 300, 70 + k), t - 0.12, db(-21))
    elif kd == "broll": add(sfx, pop(520, 900, 0.09), t + 0.05, db(-22)); add(sfx, whoosh(0.28, 500, 3600, 100 + k), t - 0.12, db(-25), pan=0.3)
    elif kd == "card":
        add(sfx, pop(520, 920, 0.09), t + 0.04, db(-19))
        if ev.get("hook"): add(sfx, thump(60, 0.4, 0.14), t + 0.02, db(-16))
    elif kd == "tick": add(sfx, bell(midi(91), 0.6, 0.16), t + 0.1, db(-23))
    elif kd == "warn": add(sfx, thump(110, 0.14, 0.05), t + 0.03, db(-18)); add(sfx, pop(400, 600, 0.08), t + 0.04, db(-22))
    elif kd == "vs_right": add(sfx, thump(60, 0.5, 0.15), t, db(-17))
    elif kd == "vs_vs": add(sfx, pop(700, 1100, 0.1), t, db(-20))
    elif kd == "alert":
        for j in range(6): add(sfx, np.sin(2 * np.pi * np.cumsum(np.full(int(0.17 * SR), 720 if j % 2 == 0 else 960)) / SR) * env_ad(int(0.17 * SR), 0.01, 0.12), t + 0.05 + j * 0.17, db(-25))
        add(sfx, thump(48, 0.7, 0.22), t, db(-12))
    elif kd == "cta": add(sfx, bell(midi(84), 1.2, 0.35), t + 0.08, db(-21)); add(sfx, bell(midi(91), 1.4, 0.45), t + 0.24, db(-23))
    elif kd == "type":
        for j in range(9): click(t + j * ev["dur"] / 9, -21)                                                                     # keyboard taps
    elif kd == "send": add(sfx, whoosh(0.28, 700, 4500, 200), t - 0.02, db(-20)); add(sfx, pop(900, 1500, 0.08), t + 0.1, db(-19))
sfx = reverb(sfx, 0.28, 0.09)

mix = music + sfx; mix[:, 0] += voice; mix[:, 1] += voice
mix *= np.clip((DUR - T) / 0.4, 0, 1)[:, None]
pk = np.abs(mix).max(); print("peak before limit %.2f dBFS" % (20 * np.log10(pk)))
rm = lambda x: float(np.sqrt(np.mean(x ** 2)))
print("rms  voice %.3f  music(ducked) %.3f  sfx %.3f" % (rm(voice), rm(music), rm(sfx)))
with wave.open(A + "/mix6.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())

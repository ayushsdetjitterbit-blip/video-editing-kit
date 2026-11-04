import os
KW = os.environ.get("KIT_WORK", os.getcwd())          # work folder (see README for the layout)
KP = os.environ.get("KIT_PROJECT", os.path.join(KW, "project"))   # HyperFrames project folder
KS = os.environ.get("KIT_SEG_PROJECT", KP + "_seg")
"""Synthesises music bed + sound effects, ducks music under the voice, writes mix.wav (stereo 44.1k)."""
import subprocess, numpy as np, wave
S = KW
SR = 44100; DUR = 35.34; N = int(DUR * SR)
rng = np.random.default_rng(7)
T = np.arange(N) / SR

def db(x): return 10 ** (x / 20)
def env_ad(n, a, d):  # attack / exponential decay
    t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
def add(buf, sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR);
    if i < 0:
        sig = sig[-i:]; i = 0
    j = min(N, i + len(sig))
    if j <= i: return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:j, 0] += sig[:j - i] * gain * l * 1.414; buf[i:j, 1] += sig[:j - i] * gain * r * 1.414

def bp_noise(n, fc_fn, width=0.6, seed=0):
    """band-limited noise whose centre frequency follows fc_fn(t) (Hz), via overlap-add STFT."""
    g = np.random.default_rng(seed); x = g.standard_normal(n)
    win = 1024; hop = 256; w = np.hanning(win); out = np.zeros(n + win)
    f = np.fft.rfftfreq(win, 1 / SR)
    for s in range(0, n - win, hop):
        fc = fc_fn((s + win / 2) / SR)
        m = np.exp(-0.5 * ((np.log2(f + 1) - np.log2(fc)) / width) ** 2)
        out[s:s + win] += np.fft.irfft(np.fft.rfft(x[s:s + win] * w) * m, win) * w
    out = out[:n]; return out / (np.abs(out).max() + 1e-9)

def whoosh(length=0.5, f0=350, f1=3800, seed=0):
    n = int(length * SR); t = np.arange(n) / SR; k = t / length
    fc = lambda tt: f0 * (f1 / f0) ** (tt / length)
    s = bp_noise(n, fc, 0.7, seed)
    e = np.sin(np.pi * np.clip(k, 0, 1)) ** 2.2 * (0.35 + 0.65 * k)
    return s * e

def pop(f0=520, f1=900, length=0.09):
    n = int(length * SR); t = np.arange(n) / SR; f = f0 + (f1 - f0) * (t / length)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.004, 0.03)

def bell(freq, length=0.9, decay=0.25):
    n = int(length * SR); t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * freq * 2.0 * t) * 1.8 * np.exp(-t / 0.08)
    return np.sin(2 * np.pi * freq * t + mod) * env_ad(n, 0.003, decay)

def thump(f=55, length=0.4, decay=0.12):
    n = int(length * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (f + 40 * np.exp(-t / 0.03)) * t) * env_ad(n, 0.003, decay)

def reverb(x, rt=0.55, mix=0.25, seed=3):
    n = int(rt * 2 * SR); t = np.arange(n) / SR
    ir = np.random.default_rng(seed).standard_normal(n) * np.exp(-t / (rt / 3)); ir[0] = 0
    ir = np.stack([ir, np.roll(ir, 97)], axis=1)
    wet = np.stack([np.convolve(x[:, c], ir[:, c], mode="full")[:len(x)] for c in range(2)], axis=1)
    wet /= (np.abs(wet).max() + 1e-9) / (np.abs(x).max() + 1e-9)
    return x * (1 - mix) + wet * mix

def midi(m): return 440 * 2 ** ((m - 69) / 12)

# ---------- music bed (real track, CC BY 4.0) ----------
import sys
TRACK = sys.argv[1]; OFFSET = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0; OUTNAME = sys.argv[3] if len(sys.argv) > 3 else "mix"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(OFFSET), "-i", f"{S}/music/{TRACK}.mp3", "-t", str(DUR + 0.5), "-ar", str(SR), "-ac", "2", f"{S}/music_seg.wav"], check=True)
with wave.open(f"{S}/music_seg.wav") as w:
    m = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float64) / 32768
music = np.zeros((N, 2)); music[:min(N, len(m))] = m[:N]
music *= 0.05 / (np.sqrt(np.mean(music ** 2)) + 1e-9)          # normalise bed level
fade = np.minimum(1, T / 1.5) * np.clip((DUR - T) / 2.2, 0, 1)
music *= fade[:, None]

# ---------- voice + ducking envelope ----------
with wave.open(f"{S}/voice.wav") as w:
    v = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
voice = np.zeros(N); voice[:min(N, len(v))] = v[:N]
win = int(0.06 * SR); e = np.sqrt(np.convolve(voice ** 2, np.ones(win) / win, mode="same"))
e = np.convolve(e, np.hanning(int(0.25 * SR)) / np.hanning(int(0.25 * SR)).sum(), mode="same")
duck = 1 - 0.62 * np.clip(e / (np.percentile(e, 90) + 1e-9), 0, 1)
music *= duck[:, None] * db(-1)

# ---------- sound effects ----------
sfx = np.zeros((N, 2))
PUNCH = [2.43, 4.30, 7.23, 11.50, 14.10, 16.80, 22.10, 26.20, 29.17, 32.50]
for i, c in enumerate(PUNCH):
    L = 0.42 if i % 2 == 0 else 0.36
    add(sfx, whoosh(L, 320 + 40 * (i % 3), 3600 + 300 * (i % 4), seed=i), c - L * 0.62, db(-19), pan=-0.5 if i % 2 == 0 else 0.5)
# paper rustle at the case-sheet cut
nR = int(0.35 * SR); knots = rng.random(14)
am = np.interp(np.arange(nR), np.linspace(0, nR, 14), knots) ** 1.5
rr = bp_noise(nR, lambda x: 4200, 0.8, 99) * am
add(sfx, rr * np.sin(np.pi * np.arange(len(rr)) / len(rr)), 19.00, db(-17))
# title: soft impact + reverse swell
add(sfx, whoosh(0.4, 300, 2500, 50), 0.0, db(-20)); add(sfx, thump(52, 0.7, 0.2), 0.42, db(-12)); add(sfx, bell(midi(84), 1.2, 0.35), 0.42, db(-31))
# pill pops
for t0 in [2.65, 4.95, 7.40, 12.00, 16.95, 19.25, 22.30, 29.35]:
    add(sfx, pop(), t0 + 0.04, db(-21))
# callout blips
for t0 in [6.47, 32.55, 33.50]:
    add(sfx, pop(1300, 1900, 0.07), t0 + 0.05, db(-22)); add(sfx, bell(midi(96), 0.5, 0.12), t0 + 0.1, db(-30))
# lift arrival ding
add(sfx, bell(midi(83), 1.0, 0.3), 27.45, db(-23), pan=0.2); add(sfx, bell(midi(79), 1.2, 0.35), 27.95, db(-24), pan=0.2)
# fetal-doppler style heartbeat under the exam shot
hb_env = np.clip((T - 16.85) / 0.3, 0, 1) * np.clip((19.05 - T) / 0.3, 0, 1)
hb = np.zeros((N, 2)); per = 60 / 138
k = 0
while 16.9 + k * per < 19.0:
    t0 = 16.9 + k * per; add(hb, thump(70, 0.25, 0.07), t0, 1.0); add(hb, thump(58, 0.25, 0.06), t0 + 0.2, 0.6); k += 1
hb *= hb_env[:, None]
sfx += hb * db(-28)
# end chime
add(sfx, bell(midi(88), 1.3, 0.4), 34.28, db(-24)); add(sfx, bell(midi(95), 1.5, 0.5), 34.42, db(-26))

sfx = reverb(sfx, 0.35, 0.12)
mix = music * db(-1) + sfx
mix[:, 0] += voice; mix[:, 1] += voice
# gentle fade-out and limiter
mix *= np.clip((DUR - T) / 0.5, 0, 1)[:, None]
pk = np.abs(mix).max(); print("peak before limit", round(20 * np.log10(pk), 2), "dBFS")
mix = np.tanh(mix / 0.92) * 0.92 if pk > 0.9 else mix
pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
with wave.open(f"{S}/{OUTNAME}.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
# also stems for checking
for name, arr in [("sfx", sfx)]:
    with wave.open(f"{S}/{name}.wav", "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(arr, -1, 1) * 32767).astype(np.int16).tobytes())

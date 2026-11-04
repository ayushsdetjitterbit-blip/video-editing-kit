"""Stage 7: sound design and final mix. Voice (cleaned) + music bed (EQ-carved, ducked under speech) + synthesised sound effects locked to the on-screen events.
Soft sounds only (taps, clicks, air), no zaps. Final loudness is measured on the encoded file and corrected to the target (default -14 LUFS, true peak <= -1.5 dBTP)."""
import json, os, subprocess, wave
import numpy as np
from scipy.signal import fftconvolve
from .util import run, log

SR = 48000
def db(x): return 10 ** (x / 20)
def env_ad(n, a, d): t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
def bp_noise(n, fc_fn, width=0.6, seed=0):
    g = np.random.default_rng(seed); x = g.standard_normal(n); win = 1024; hop = 256; w = np.hanning(win); out = np.zeros(n + win); f = np.fft.rfftfreq(win, 1 / SR)
    for s in range(0, max(1, n - win), hop):
        fc = fc_fn((s + win / 2) / SR); m = np.exp(-0.5 * ((np.log2(f + 1) - np.log2(fc)) / width) ** 2)
        out[s:s + win] += np.fft.irfft(np.fft.rfft(x[s:s + win] * w) * m, win) * w
    out = out[:n]; return out / (np.abs(out).max() + 1e-9)
def whoosh(length=0.5, f0=350, f1=3800, seed=0):
    n = int(length * SR); k = np.arange(n) / SR / length; s = bp_noise(n, lambda tt: f0 * (f1 / f0) ** (tt / length), 0.7, seed)
    return s * np.sin(np.pi * np.clip(k, 0, 1)) ** 2.2 * (0.35 + 0.65 * k)
def pop(f0=520, f1=900, length=0.09):
    n = int(length * SR); t = np.arange(n) / SR; f = f0 + (f1 - f0) * (t / length); return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.004, 0.03)
def bell(freq, length=0.9, decay=0.25):
    n = int(length * SR); t = np.arange(n) / SR; mod = np.sin(2 * np.pi * freq * 2.0 * t) * 1.8 * np.exp(-t / 0.08); return np.sin(2 * np.pi * freq * t + mod) * env_ad(n, 0.003, decay)
def thump(f=55, length=0.4, decay=0.12): n = int(length * SR); t = np.arange(n) / SR; return np.sin(2 * np.pi * (f + 40 * np.exp(-t / 0.03)) * t) * env_ad(n, 0.003, decay)
def midi(m): return 440 * 2 ** ((m - 69) / 12)
def reverb(x, rt=0.28, mix=0.09, seed=3):
    n = int(rt * 2 * SR); t = np.arange(n) / SR; ir = np.random.default_rng(seed).standard_normal(n) * np.exp(-t / (rt / 3)); ir[0] = 0
    ir = np.stack([ir, np.roll(ir, 97)], axis=1); wet = np.stack([fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], axis=1)
    wet /= (np.abs(wet).max() + 1e-9) / (np.abs(x).max() + 1e-9); return x * (1 - mix) + wet * mix

def _rd(p): w = wave.open(p); return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768

def build(cfg, work, project, dur):
    ac = cfg["audio"]; N = int((dur + 0.05) * SR); T = np.arange(N) / SR; sched = json.load(open(os.path.join(work, "schedule.json")))
    v = _rd(os.path.join(work, "voice_enh.wav")); voice = np.zeros(N); voice[:min(N, len(v))] = v[:N]
    music = np.zeros((N, 2)); vrms = np.sqrt(np.mean(voice ** 2)) + 1e-9
    if ac.get("music"):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "0.3", "-t", str(dur + 0.1), "-i", ac["music"], "-ac", "2", "-ar", str(SR), "-af", "highpass=f=70,lowpass=f=12000,equalizer=f=2200:t=q:w=0.8:g=-3.5", "-f", "f32le", "-"], capture_output=True).stdout
        mu = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64); music[:min(N, len(mu))] = mu[:N]
        music *= vrms * db(ac["music_level_db"]) / (np.sqrt(np.mean(music ** 2)) + 1e-9)            # level relative to the voice, before ducking
        music *= (np.minimum(1, T / 1.2) * np.clip((dur - T) / 2.6, 0, 1))[:, None]
        win = int(0.06 * SR); e = np.sqrt(np.convolve(voice ** 2, np.ones(win) / win, mode="same")); k = np.hanning(int(0.30 * SR)); e = np.convolve(e, k / k.sum(), mode="same")
        music *= (1 - 0.62 * np.clip(e / (np.percentile(e, 90) + 1e-9), 0, 1))[:, None]               # duck under speech
    sfx = np.zeros((N, 2))
    def add(sig, t0, gain=1.0, pan=0.0):
        i = int(t0 * SR)
        if i < 0: sig = sig[-i:]; i = 0
        j = min(N, i + len(sig))
        if j <= i: return
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4); sfx[i:j, 0] += sig[:j - i] * gain * l * 1.414; sfx[i:j, 1] += sig[:j - i] * gain * r * 1.414
    if ac["sfx"]:
        evs = sched["events"]
        if evs and evs[0]["kind"] == "card" and evs[0].get("hook") and evs[0]["t"] < 1.5:
            add(whoosh(0.45, 300, 3200, 5), 0.0, db(-18)); add(thump(55, 0.6, 0.18), 0.06, db(-14)); add(bell(midi(88), 0.9, 0.3), 0.12, db(-29))
        for i, t in enumerate(sched["seams"]): add(whoosh(0.2, 600, 4200, 10 + i), t - 0.12, db(-33), pan=-0.4 if i % 2 else 0.4)
        for k, ev in enumerate(evs):
            t, kd = ev["t"], ev["kind"]
            if kd == "broll": add(pop(520, 900, 0.09), t + 0.05, db(-22)); add(whoosh(0.28, 500, 3600, 100 + k), t - 0.12, db(-25), pan=0.3)
            elif kd == "card":
                add(pop(520, 920, 0.09), t + 0.04, db(-19))
                if ev.get("hook"): add(thump(60, 0.4, 0.14), t + 0.02, db(-16))
            elif kd == "tick": add(bell(midi(91), 0.6, 0.16), t + 0.1, db(-23))
            elif kd == "warn": add(thump(110, 0.14, 0.05), t + 0.03, db(-18)); add(pop(400, 600, 0.08), t + 0.04, db(-22))
            elif kd == "vs_right": add(thump(60, 0.5, 0.15), t, db(-17))
            elif kd == "cta": add(bell(midi(84), 1.2, 0.35), t + 0.08, db(-21)); add(bell(midi(91), 1.4, 0.45), t + 0.24, db(-23))
            elif kd == "send": add(whoosh(0.28, 700, 4500, 200), t - 0.02, db(-20)); add(pop(900, 1500, 0.08), t + 0.1, db(-19))
        sfx = reverb(sfx)
    mix = music + sfx; mix[:, 0] += voice; mix[:, 1] += voice; mix *= np.clip((dur - T) / 0.4, 0, 1)[:, None]
    p = os.path.join(work, "mix.wav")
    with wave.open(p, "wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    T_ = ac["target_lufs"]
    r = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", p, "-af", f"loudnorm=I={T_}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    d = json.loads(r[r.rfind("{"):]); os.makedirs(os.path.join(project, "assets"), exist_ok=True)
    run(["ffmpeg", "-v", "error", "-y", "-i", p, "-af", f"loudnorm=I={T_}:TP=-1.5:LRA=11:measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}:linear=true",
         "-ar", str(SR), "-c:a", "aac", "-b:a", "256k", os.path.join(project, "assets", "mix.m4a")])
    log(f"mix: voice {20 * np.log10(vrms):.1f} dBFS rms, music {'on' if ac.get('music') else 'off'}, {len(sched['events'])} sound events, target {T_} LUFS")

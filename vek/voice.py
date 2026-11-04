"""Stage 4: the voice. Rebuilt from the ORIGINAL audio at the exact same cut samples (no AAC generation loss), then cleaned without changing its character:
noise reduction (noise profile taken from this recording's own pauses), light EQ, de-esser, gentle compression, loudness normalisation (two-pass).
A verification report compares noise, SNR and pitch before/after, so a bad setting is visible instead of silently shipped."""
import json, os, subprocess, wave
import numpy as np
from .util import run, log

SR = 48000

def _rd(p):
    w = wave.open(p); return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
def _wr(p, x):
    with wave.open(p, "wb") as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

def build_raw(work, fps):
    spf = SR // fps; x = _rd(os.path.join(work, "a48.wav")); tl = json.load(open(os.path.join(work, "timeline.json")))
    f = int(0.006 * SR); ramp = np.linspace(0, 1, f); out = []
    for A, B in tl["frames"]:
        s = x[A * spf:B * spf].copy()
        if len(s) > 2 * f: s[:f] *= ramp; s[-f:] *= ramp[::-1]
        out.append(s)
    y = np.concatenate(out); _wr(os.path.join(work, "voice_raw.wav"), y); return y

def _lufs(path):
    import re
    r = run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    m = re.findall(r"I:\s+(-?\d+\.?\d*)\s+LUFS", r); return float(m[-1]) if m else None

def enhance(work, cfg):
    x = _rd(os.path.join(work, "voice_raw.wav")); H = 2048; vc = cfg["voice"]
    fr = x[:len(x) // H * H].reshape(-1, H); e = 10 * np.log10((fr ** 2).mean(1) + 1e-12)
    quiet = fr[e <= np.percentile(e, 8)].reshape(-1); y = x
    if vc["enhance"] and vc["noise_reduce"] > 0 and len(quiet) > 1.0 * SR:
        import noisereduce as nr
        y = nr.reduce_noise(y=x, sr=SR, y_noise=quiet, stationary=True, prop_decrease=float(vc["noise_reduce"]), n_fft=2048, win_length=2048, hop_length=512,
                            freq_mask_smooth_hz=400, time_mask_smooth_ms=64)
    else: log("voice: no usable pauses for a noise profile (or noise reduction off) - skipping denoise")
    _wr(os.path.join(work, "voice_nr.wav"), y)
    chain = ("highpass=f=80,equalizer=f=300:t=q:w=1.2:g=-1.5,equalizer=f=3000:t=q:w=0.9:g=1.3,highshelf=f=7000:g=0.6,deesser=i=0.25:m=0.5:f=0.5,"
             "acompressor=threshold=-20dB:ratio=2.0:attack=15:release=220:makeup=1") if vc["enhance"] else "anull"
    T = vc["target_lufs"]; nr_wav = os.path.join(work, "voice_nr.wav")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", nr_wav, "-af", chain + f",loudnorm=I={T}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    d = json.loads(r[r.rfind("{"):])
    run(["ffmpeg", "-v", "error", "-y", "-i", nr_wav, "-af", chain + f",loudnorm=I={T}:TP=-1.5:LRA=11:measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}:linear=true",
         "-ar", str(SR), "-ac", "1", os.path.join(work, "voice_enh.wav")])
    # verification on identical frames
    a = _rd(os.path.join(work, "voice_enh.wav")); n = min(len(a), len(x)); a, b = a[:n], x[:n]
    fb = b[:n // H * H].reshape(-1, H); fa = a[:n // H * H].reshape(-1, H); eb = 10 * np.log10((fb ** 2).mean(1) + 1e-12)
    ni = eb <= np.percentile(eb, 8); si = eb >= np.percentile(eb, 60); lv = lambda f: 10 * np.log10((f ** 2).mean() + 1e-12)
    rep = dict(snr_before=round(lv(fb[si]) - lv(fb[ni]), 1), snr_after=round(lv(fa[si]) - lv(fa[ni]), 1), lufs_after=_lufs(os.path.join(work, "voice_enh.wav")),
               peak_dbfs=round(20 * np.log10(np.abs(a).max() + 1e-9), 1), clipped=int((np.abs(a) > 0.999).sum()))
    def f0(F, idx):
        out = []
        for f in F[idx][::2]:
            f = f - f.mean(); ac = np.correlate(f, f, "full")[H - 1:]; lo, hi = int(SR / 350), int(SR / 75); pk = ac[lo:hi].argmax() + lo
            out.append(SR / pk if ac[pk] / (ac[0] + 1e-12) > 0.5 else np.nan)
        return np.array(out)
    pb, pa = f0(fb, si), f0(fa, si); ok = ~np.isnan(pb) & ~np.isnan(pa)
    if ok.sum() > 10: rep["pitch_change_pct"] = round(float(abs(np.nanmedian(pa[ok]) / np.nanmedian(pb[ok]) - 1) * 100), 2)
    log(f"voice: SNR {rep['snr_before']} -> {rep['snr_after']} dB, {rep['lufs_after']} LUFS, pitch change {rep.get('pitch_change_pct')}%")
    if rep["snr_after"] < rep["snr_before"] - 1: log("voice: WARNING noise reduction lowered the SNR; set voice.noise_reduce lower")
    json.dump(rep, open(os.path.join(work, "voice_report.json"), "w"))
    return rep

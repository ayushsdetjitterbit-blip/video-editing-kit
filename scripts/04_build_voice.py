"""Step 4: rebuild the voice from the ORIGINAL audio at the exact same cuts (no AAC generation loss).
Needs a44.wav (ffmpeg -i src.mp4 -vn -ac 1 -ar 44100 a44.wav) and timeline.json. Writes audio/voice_aligned_raw.wav."""
import numpy as np, wave, json, os
os.makedirs("audio", exist_ok=True)
w = wave.open("a44.wav"); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
keep = json.load(open("timeline.json"))["fr"]; out = []; f = int(0.006 * 44100); ramp = np.linspace(0, 1, f)
for A, B in keep:
    s = x[A * 1470:B * 1470].copy(); s[:f] *= ramp; s[-f:] *= ramp[::-1]; out.append(s)
y = np.concatenate(out)
with wave.open("audio/voice_aligned_raw.wav", "wb") as o:
    o.setnchannels(1); o.setsampwidth(2); o.setframerate(44100); o.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())

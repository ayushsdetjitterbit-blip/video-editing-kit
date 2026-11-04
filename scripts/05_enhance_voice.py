import numpy as np, wave, subprocess, json, noisereduce as nr
A="audio/"; SR=44100
def rd(p):
    w=wave.open(p); return np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float64)/32768
def wr(p,x):
    with wave.open(p,"wb") as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(x,-1,1)*32767).astype(np.int16).tobytes())
x=rd(A+"voice_aligned_raw.wav"); H=2048
fr=x[:len(x)//H*H].reshape(-1,H); e=10*np.log10((fr**2).mean(1)+1e-12)
noise=fr[(e<=np.percentile(e,8))].reshape(-1)             # the room's own noise, taken from the pauses
print("noise profile from %.1fs of pauses (level %.1f dBFS)"%(len(noise)/SR,10*np.log10((noise**2).mean())))
y=nr.reduce_noise(y=x,sr=SR,y_noise=noise,stationary=True,prop_decrease=0.85,n_fft=2048,win_length=2048,hop_length=512,freq_mask_smooth_hz=400,time_mask_smooth_ms=64)
wr(A+"voice_nr.wav",y)
CH=("highpass=f=80,equalizer=f=300:t=q:w=1.2:g=-1.5,equalizer=f=3000:t=q:w=0.9:g=1.3,highshelf=f=7000:g=0.6,deesser=i=0.25:m=0.5:f=0.5,"
    "volume=14dB,acompressor=threshold=-20dB:ratio=2.0:attack=15:release=220:makeup=1")
r=subprocess.run(["ffmpeg","-hide_banner","-y","-i",A+"voice_nr.wav","-af",CH+",loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json","-f","null","-"],capture_output=True,text=True).stderr
d=json.loads(r[r.rfind("{"):]); 
subprocess.run(["ffmpeg","-v","error","-y","-i",A+"voice_nr.wav","-af",CH+f",loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}:linear=true","-ar","44100","-ac","1",A+"voice_enh.wav"],check=True)
# ---- verification (same frames in both signals) ----
b=x; a=rd(A+"voice_enh.wav"); n=min(len(a),len(b)); a,b=a[:n],b[:n]
fb=b[:n//H*H].reshape(-1,H); fa=a[:n//H*H].reshape(-1,H); eb=10*np.log10((fb**2).mean(1)+1e-12)
ni=eb<=np.percentile(eb,8); si=eb>=np.percentile(eb,60)
lv=lambda f:10*np.log10((f**2).mean()+1e-12)
for nm,F in (("original",fb),("enhanced",fa)): print("%-9s noise %6.1f dBFS | speech %6.1f dBFS | SNR %5.1f dB"%(nm,lv(F[ni]),lv(F[si]),lv(F[si])-lv(F[ni])))
def f0s(F,idx):
    out=[]
    for f in F[idx][::2]:
        f=f-f.mean(); ac=np.correlate(f,f,"full")[H-1:]; lo,hi=int(SR/350),int(SR/75); pk=ac[lo:hi].argmax()+lo
        out.append(SR/pk if ac[pk]/ac[0]>0.5 else np.nan)
    return np.array(out)
pb,pa=f0s(fb,si),f0s(fa,si); ok=~np.isnan(pb)&~np.isnan(pa)
print("pitch on identical voiced frames: median original %.1f Hz | enhanced %.1f Hz | frames where pitch moved >2%%: %d of %d"%(np.nanmedian(pb[ok]),np.nanmedian(pa[ok]),int((abs(pa[ok]/pb[ok]-1)>0.02).sum()),int(ok.sum())))
f=np.fft.rfftfreq(4096,1/SR)
def P(F,idx): 
    s=F[idx][:, :4096] if F.shape[1]>=4096 else F[idx]; return (np.abs(np.fft.rfft(s*np.hanning(s.shape[1]),axis=1))**2).mean(0)
Pb,Pa=P(fb,si),P(fa,si); ff=np.fft.rfftfreq(fb.shape[1],1/SR)
print("tonal balance change on speech (level-matched), dB:")
for lo,hi in [(80,250),(250,500),(500,1000),(1000,2000),(2000,4000),(4000,8000),(8000,16000)]:
    m=(ff>=lo)&(ff<hi); print("  %5d-%5d Hz %+5.1f"%(lo,hi,10*np.log10(Pa[m].sum()/Pb[m].sum())-10*np.log10(Pa.sum()/Pb.sum())))
print("final peak %.1f dBFS, clipped samples %d"%(20*np.log10(np.abs(a).max()),int((np.abs(a)>0.999).sum())))

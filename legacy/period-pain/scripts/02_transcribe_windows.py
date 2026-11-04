import json,wave,numpy as np
from faster_whisper import WhisperModel
w=wave.open("a16.wav"); x=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768
S=json.load(open("runs.json")); win=[list(S[0])]
for a,b in S[1:]:
    if a-win[-1][1]<0.25: win[-1][1]=b
    else: win.append([a,b])
print(len(win),"windows",flush=True)
m=WhisperModel("large-v3",device="cpu",compute_type="int8",cpu_threads=4); out=[]
for a,b in win:
    A=max(0,a-0.15);B=min(len(x)/16000,b+0.15)
    seg,_=m.transcribe(x[int(A*16000):int(B*16000)],language="hi",word_timestamps=True,vad_filter=False,condition_on_previous_text=False,beam_size=5,temperature=0)
    ws=[]
    for s in seg:
        for q in s.words: ws.append(dict(w=q.word.strip(),s=round(A+q.start,2),e=round(A+q.end,2),p=round(q.probability,2)))
    out.append(dict(a=round(a,2),b=round(b,2),words=ws)); print(round(a,2),round(b,2)," ".join(q["w"] for q in ws),flush=True)
json.dump(out,open("tr2.json","w"),ensure_ascii=False,indent=1); print("DONE")

import subprocess, numpy as np, cv2, time
cv2.setNumThreads(4)
W,H=1080,1920; FS=W*H*3
g=subprocess.Popen(["ffmpeg","-v","error","-i","presenter2.mp4","-f","rawvideo","-pix_fmt","bgr24","-"],stdout=subprocess.PIPE,bufsize=FS*3)
s=subprocess.Popen(["ffmpeg","-v","error","-i","clean_master.mp4","-vf","scale=1080:1920:flags=lanczos","-f","rawvideo","-pix_fmt","bgr24","-"],stdout=subprocess.PIPE,bufsize=FS*3)
e=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","bgr24","-s","1080x1920","-r","30","-i","-","-c:v","libx264","-crf","13","-preset","medium","-pix_fmt","yuv420p","-g","30","-movflags","+faststart","presenter3.mp4"],stdin=subprocess.PIPE)
xs=np.arange(256,dtype=np.float32)
# light, natural S-curve (iPhone-like contrast), no highlight blow
lut=np.clip(np.where(xs<190,xs,190+(xs-190)*0.75),0,255); lut=np.clip(lut+0.06*(xs-128)*(1-np.abs(xs-128)/128)*2,0,255).astype(np.uint8)
n=0;t0=time.time()
while True:
    a=g.stdout.read(FS); b=s.stdout.read(FS)
    if len(a)<FS or len(b)<FS: break
    G=np.frombuffer(a,np.uint8).reshape(H,W,3).astype(np.float32); S=np.frombuffer(b,np.uint8).reshape(H,W,3).astype(np.float32)
    # keep GPEN's detail, take lighting + skin tone from the real footage
    corr=cv2.GaussianBlur(S,(0,0),9)-cv2.GaussianBlur(G,(0,0),9)
    out=np.clip(G+np.clip(corr,-22,22)*0.85,0,255).astype(np.uint8)
    out=cv2.LUT(out,lut)
    e.stdin.write(out.tobytes()); n+=1
    if n%300==0: print(n,round(time.time()-t0),flush=True)
e.stdin.close(); e.wait(); print("DONE",n,flush=True)

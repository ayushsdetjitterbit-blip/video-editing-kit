import os
KW = os.environ.get("KIT_WORK", os.getcwd())
import sys, subprocess, numpy as np, cv2, onnxruntime as ort, time
S=KW
import cv2
ort.set_default_logger_severity(4); cv2.setNumThreads(2)
M=S+"/v8/models/"
raw=subprocess.run(["ffmpeg","-v","error","-i","clean_dn.mp4","-f","rawvideo","-pix_fmt","bgr24","-"],capture_output=True).stdout
A0,A1=int(sys.argv[1]),int(sys.argv[2]); fr=np.frombuffer(raw,np.uint8).reshape(-1,850,478,3)[A0:A1]; n=len(fr); print(A0,A1,n,flush=True)
cc=cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml")
gp=ort.InferenceSession(M+"gpen_bfr_512.onnx",providers=["CPUExecutionProvider"],sess_options=(lambda o:(setattr(o,"intra_op_num_threads",3),o)[1])(ort.SessionOptions()))
mn=ort.InferenceSession(M+"modnet.onnx",providers=["CPUExecutionProvider"]); mnn=mn.get_inputs()[0].name
Y,X=np.mgrid[0:1920,0:1080].astype(np.float32)
vig=(0.9+0.1*(1-np.clip(np.sqrt(((X-540)/700)**2+((Y-800)/1200)**2),0,1)))[...,None]
yy,xx=np.mgrid[0:600,0:600].astype(np.float32)
box=None; pm=None; dface=None
rng=np.random.default_rng(1)
xs=np.arange(256,dtype=np.float32); lut=np.clip(np.where(xs<185,xs,185+(xs-185)*0.62)*0.97,0,255).astype(np.uint8)
enc=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","bgr24","-s","1080x1920","-r","30","-i","-","-c:v","libx264","-crf","14","-preset","medium","-pix_fmt","yuv420p","-g","30",f"chunks2/p_{A0:05d}.mp4"],stdin=subprocess.PIPE)
t0=time.time()
for i,f in enumerate(fr):
    g=cv2.equalizeHist(cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)); r=cc.detectMultiScale(g,1.1,5,minSize=(100,100),maxSize=(300,300))
    if len(r):
        x,y,w,h=max(r,key=lambda b:b[2]*b[3]); b=np.array([x+w/2,y+h/2,w],float)*(1080/478); box=b if box is None else .8*box+.2*b
    base=cv2.resize(f,(1080,1920),interpolation=cv2.INTER_LANCZOS4)
    # matte (temporal smoothing)
    x_=cv2.resize(f,(480,864)); x_=((cv2.cvtColor(x_,cv2.COLOR_BGR2RGB).astype(np.float32)/255-.5)/.5).transpose(2,0,1)[None]
    if i%2==0:
        m=mn.run(None,{mnn:x_})[0][0,0]; m=cv2.resize(m,(1080,1920),interpolation=cv2.INTER_CUBIC).clip(0,1); pm=m if pm is None else .5*m+.5*pm
    out=base
    if i%2==1 and dface is not None:
        x0,y0,side,D=dface; out=base.copy(); out[y0:y0+side,x0:x0+side]=np.clip(base[y0:y0+side,x0:x0+side].astype(np.float32)+D,0,255).astype(np.uint8)
    elif box is not None:                                   # GPEN face restore, feathered paste-back
        cx,cy,w=box; side=min(1060,int(w*1.75)); cy=cy-side*.02; x0=int(max(0,min(1080-side,cx-side/2))); y0=int(max(0,min(1920-side,cy-side/2)))
        crop=base[y0:y0+side,x0:x0+side]; inp=cv2.cvtColor(cv2.resize(crop,(512,512),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2RGB).astype(np.float32)/127.5-1
        o=gp.run(None,{"input":inp.transpose(2,0,1)[None]})[0][0].transpose(1,2,0); o=cv2.cvtColor(np.clip((o+1)*127.5,0,255).astype(np.uint8),cv2.COLOR_RGB2BGR)
        o=cv2.resize(o,(side,side),interpolation=cv2.INTER_CUBIC)
        yy_,xx_=np.mgrid[0:side,0:side].astype(np.float32); d=np.sqrt(((xx_-side/2)/(side*.47))**2+((yy_-side/2)/(side*.5))**2)
        mk=np.clip((1-d)/.35,0,1)[...,None]*.85
        out=base.copy(); out[y0:y0+side,x0:x0+side]=(crop*(1-mk)+o*mk).astype(np.uint8); dface=(x0,y0,side,out[y0:y0+side,x0:x0+side].astype(np.float32)-crop.astype(np.float32))
    out=cv2.LUT(np.clip(out,0,255).astype(np.uint8),lut)
    enc.stdin.write(out.tobytes())
    if i%30==0: print(A0+i,round(time.time()-t0),flush=True)
enc.stdin.close(); enc.wait(); print("DONE",time.time()-t0,flush=True)

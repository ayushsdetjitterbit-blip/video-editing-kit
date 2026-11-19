"""Neural detail for small sources: Real-ESRGAN (general-x4v3, ONNX, CPU) on every Nth frame, carried to the frames in between by motion tracking.
Running the network on every frame would take hours on a CPU and would flicker; instead the *detail layer* D = neural(frame) - plain_upscale(frame) is computed on
keyframes, warped onto the neighbouring frames with optical flow, and only used where the warp really matches the frame (confidence mask), so moving
hands, hair and cloth never get ghost detail."""
import numpy as np, cv2, os
from .util import log

class Detail:
    def __init__(self, model_path, sw, sh, nw, nh, stride=5, threads=4):
        import onnxruntime as ort
        so = ort.SessionOptions(); so.intra_op_num_threads = threads; so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.s = ort.InferenceSession(model_path, so, providers=["CPUExecutionProvider"]); self.name = self.s.get_inputs()[0].name
        self.sw, self.sh, self.nw, self.nh, self.stride = sw, sh, nw, nh, stride; self.K = nw / sw
        self.gx, self.gy = np.meshgrid(np.arange(nw, dtype=np.float32), np.arange(nh, dtype=np.float32))
        self.sgx, self.sgy = np.meshgrid(np.arange(sw, dtype=np.float32), np.arange(sh, dtype=np.float32))
        self.flow = dict(pyr_scale=0.5, levels=4, winsize=21, iterations=3, poly_n=7, poly_sigma=1.5, flags=0)

    def _sr4(self, bgr, tile=128, pad=12, flat_std=0.012):
        """x4 neural upscale with overlapped tiles; flat tiles (plain wall, sky) get a cheap upscale instead."""
        h, w = bgr.shape[:2]; rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        step = tile - 2 * pad; ph = (-(h - 2 * pad)) % step; pw = (-(w - 2 * pad)) % step
        rgb = np.pad(rgb, ((pad, pad + ph), (pad, pad + pw), (0, 0)), mode="reflect"); H, W = rgb.shape[:2]
        out = cv2.resize(rgb, (W * 4, H * 4), interpolation=cv2.INTER_LANCZOS4)
        for y in range(0, H - tile + 1, step):
            for x in range(0, W - tile + 1, step):
                t = rgb[y:y + tile, x:x + tile]
                if t.std() < flat_std: continue
                o = self.s.run(None, {self.name: t.transpose(2, 0, 1)[None]})[0][0].transpose(1, 2, 0)
                out[(y + pad) * 4:(y + tile - pad) * 4, (x + pad) * 4:(x + tile - pad) * 4] = o[pad * 4:(tile - pad) * 4, pad * 4:(tile - pad) * 4]
        out = out[pad * 4:(pad + h) * 4, pad * 4:(pad + w) * 4]
        return cv2.cvtColor((out.clip(0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)

    def keyframe(self, frame):
        nsr = cv2.resize(self._sr4(frame), (self.nw, self.nh), interpolation=cv2.INTER_AREA).astype(np.float32)
        return nsr - cv2.resize(frame, (self.nw, self.nh), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)

    def _warp(self, D, g_t, g_k, f_t, f_k):
        flow = cv2.calcOpticalFlowFarneback(g_t, g_k, None, **self.flow)
        fl = cv2.resize(flow, (self.nw, self.nh), interpolation=cv2.INTER_LINEAR) * self.K
        Dw = cv2.remap(D, self.gx + fl[..., 0], self.gy + fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        kw = cv2.remap(f_k, self.sgx + flow[..., 0], self.sgy + flow[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        err = cv2.GaussianBlur(np.abs(kw - f_t.astype(np.float32)).mean(2), (0, 0), 2.0)                # does the warped keyframe look like this frame?
        conf = cv2.resize(np.exp(-(err / 7.0) ** 2), (self.nw, self.nh), interpolation=cv2.INTER_LINEAR)
        return Dw, conf

    def layer(self, frames, i, cache, gray):
        """Detail residual (float32, cover size) for frame i of `frames`; `cache` keeps at most two keyframes."""
        n = len(frames); k1 = (i // self.stride) * self.stride; k2 = min(k1 + self.stride, n - 1)
        if i == n - 1: k1 = k2 = i
        for k in (k1, k2):
            if k not in cache: cache[k] = self.keyframe(frames[k])
        for k in [k for k in cache if k < k1 or k > k2]: del cache[k]
        acc = np.zeros((self.nh, self.nw, 3), np.float32); ws = np.zeros((self.nh, self.nw), np.float32)
        for k, wt in ((k1, 1.0 if k1 == k2 else (k2 - i) / (k2 - k1)), (k2, 0.0 if k1 == k2 else (i - k1) / (k2 - k1))):
            if wt <= 0: continue
            if k == i: Dw, conf = cache[k], np.ones((self.nh, self.nw), np.float32)
            else: Dw, conf = self._warp(cache[k], gray(i), gray(k), frames[i], frames[k])
            w = wt * conf; acc += Dw * w[..., None]; ws += w
        return acc / np.maximum(ws, 1e-3)[..., None] * np.minimum(1.0, ws)[..., None]

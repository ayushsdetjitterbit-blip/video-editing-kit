# Look decisions (iPhone-style grade)

Goal: natural, "iPhone" look. Tested on the same 4-second clip:

- **A (version 4):** brightness x0.93 + contrast 1.06 -> still bright/flat, whites glowed.
- **B / C:** lifted shadows + extra saturation + unsharp -> too bright and shiny.
- **D / E:** + CLAHE local contrast, glow, vignette -> shinier; rejected.
- **P1 / P2 / P3:** tone-curve with a strong highlight shoulder, no glow. **P1 chosen.**
  `curves 0/0.01 0.3/0.29 0.5/0.47 0.7/0.64 0.85/0.77 1/0.90`, saturation 1.04, light luma unsharp.
- **Automatic "de-shine"** (flatten bright blobs on the face with a smooth gain): left grey, patchy skin -> rejected.
- **R (original footage, only denoised + sharpened, no face restoration):** most natural skin but softer.

Why the face shines: the original footage is lit unevenly (nose ~190 vs cheeks ~119 on a 0-255 scale), and GPEN adds glossy highlights.
The real fix is the original phone recording (or re-shooting with softer, side-lit light).

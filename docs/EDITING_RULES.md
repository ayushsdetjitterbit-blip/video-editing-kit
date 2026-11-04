# Editing rules (from your notes in this project, plus ideas from herk-edit-kit)

**Cuts**
- Cut between phrases, never inside one. Keep ~70 ms before and ~100 ms after each phrase; natural beats after a comma stay.
- Keep only the best of repeated takes; drop a filler only when there is silence on both sides of it.
- Cuts are frame-exact (30 fps, 1470 samples/frame at 44.1 kHz) with 6 ms audio fades.

**Visuals**
- Face always visible except in planned full-screen B-roll moments; never cover the mouth. Check every render with the face-box overlap test.
- Cards low (chest height), not covering the body; no heavy blurs or glows in the background (they read as noise).
- B-roll must match the topic and the audience: women's health here, so no men and no random nature shots.
- Prefer video B-roll that moves (slow zoom); stills only for short, clean moments. Never invent numbers or results.
- Don't brighten or smooth the face. Restoration tools make skin glossy: keep their detail but take light and colour from the real footage.

**Captions:** one dark pill, white text, word-by-word fill, 1-4 words per chunk, never over the face, contrast checked.

**Sound:** voice untouched in character (same pitch), music ~11 dB under the voice and ducked, soft SFX tied to visible actions (avoid a whoosh on every cut), target -14 LUFS, measure the final encoded file.

**Process:** test on a 2-second clip before processing the full video; render only the changed segment when possible.

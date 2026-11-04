"""Fast unit tests (no video, no models): run with  python -m unittest discover -s tests"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vek import cut, captions, picture, transcribe, config, compose
from vek.util import deep_merge

def W(a, b, text, p=0.9): return dict(a=a, b=b, text=text, words=[dict(w=t, p=p, s=a, e=b) for t in text.split()])
CFG = dict(cut=dict(drop_windows=[], drop_fillers=True, drop_repeats=True, repeat_similarity=.82, pad_before=.07, pad_after=.1, tail_pad=.1, start_overrides={}, end_overrides={}))

class CutTests(unittest.TestCase):
    def test_filler_only_window_is_dropped(self):
        keep, dropped = cut.decide([W(0, 2, "hello there everyone"), W(2.5, 3, "um"), W(3.5, 6, "today we talk")], CFG, "en")
        self.assertEqual(keep, [0, 2]); self.assertEqual(dropped[0]["reason"], "filler only")
    def test_sentence_inside_window_never_cut(self):
        keep, _ = cut.decide([W(0, 3, "um I think this works")], CFG, "en"); self.assertEqual(keep, [0])     # filler inside a sentence stays
    def test_repeated_take_keeps_later(self):
        keep, dropped = cut.decide([W(0, 2, "this is the best sentence"), W(2.8, 5, "this is the best sentence")], CFG, "en")
        self.assertEqual(keep, [1]); self.assertEqual(dropped[0]["index"], 0)
    def test_false_start_dropped(self):
        keep, dropped = cut.decide([W(0, 1.5, "today we will talk"), W(2, 5, "today we will talk about heart health")], CFG, "en")
        self.assertEqual(keep, [1]); self.assertEqual(dropped[0]["reason"], "false start")
    def test_different_sentences_kept(self):
        keep, _ = cut.decide([W(0, 2, "first point is sleep"), W(2.6, 5, "second point is food")], CFG, "en"); self.assertEqual(keep, [0, 1])
    def test_frames_are_whole_numbers_and_ordered(self):
        keep, _ = cut.build([W(0.6, 2.0, "a b c"), W(2.3, 4.0, "d e f")], CFG, 30, 5.0, "en")
        for A, B, _ in keep: self.assertIsInstance(A, int); self.assertLess(A, B)
        self.assertTrue(all(keep[i][1] <= keep[i + 1][0] for i in range(len(keep) - 1)))
    def test_sample_exact_for_all_fps(self):
        for fps in (24, 25, 30, 50, 60): self.assertEqual(48000 % fps, 0)

class LoopTests(unittest.TestCase):
    def test_loop_detected_and_collapsed(self):
        w = [dict(w=x) for x in ("a b " + "x y z " * 4 + "end").split()]
        self.assertTrue(transcribe.has_loop(w)); self.assertEqual(len(transcribe.collapse_loops(w)), 2 + 3 + 1)
    def test_natural_repeat_untouched(self):
        w = [dict(w=x) for x in "I really really like it".split()]; self.assertFalse(transcribe.has_loop(w)); self.assertEqual(len(transcribe.collapse_loops(w)), 5)

class LookTests(unittest.TestCase):
    def test_dark_video_untouched_bright_protected(self):
        dark = picture.look_params(dict(p50=.25, p99=.78, width=1080), "natural"); bright = picture.look_params(dict(p50=.62, p99=.97, width=478, face_luma=.65), "natural")
        self.assertLess(dark["strength"], .25); self.assertGreater(bright["strength"], .9)
    def test_curve_monotonic_and_never_brightens(self):
        for st in (dict(p50=.2, p99=.7, width=1080), dict(p50=.6, p99=1.0, width=478)):
            pts = [tuple(map(float, p.split("/"))) for p in picture.look_params(st, "natural")["curves"].split()]
            ys = [y for _, y in pts]; self.assertEqual(ys, sorted(ys))
            for x, y in pts[1:]: self.assertLessEqual(y, x + 0.011)       # highlights are only ever compressed
    def test_look_off(self): self.assertIsNone(picture.look_params(dict(p50=.5, p99=.9, width=700), "off"))

class CaptionTests(unittest.TestCase):
    def test_groups_are_ordered_and_inside_video(self):
        tl = dict(keep=[[0, 5], [6, 10]]); M = captions.mapper(tl)
        ch = [(0.5, "hello there you", 5), (1.5, "this is a test", 5), (6.5, "second part here", 10)]
        g = captions.build_groups(ch, M, 9.0, 30)
        self.assertEqual(len(g), 3)
        for a, b in zip(g, g[1:]): self.assertLessEqual(a["t1"], b["t0"] + 0.05)
        self.assertTrue(all(0 < x["t0"] < x["t1"] <= 9.0 for x in g)); self.assertTrue(all(len(x["words"]) == len(x["st"]) for x in g))
    def test_mapper_skips_cut_gaps(self):
        M = captions.mapper(dict(keep=[[0, 5], [6, 10]])); self.assertEqual(M(6.5), 5.5)

class ConfigTests(unittest.TestCase):
    def test_deep_merge(self): self.assertEqual(deep_merge(dict(a=dict(b=1, c=2)), dict(a=dict(b=9)))["a"], dict(b=9, c=2))
    def test_storyboard_rejects_unknown_type(self):
        import tempfile, yaml
        p = tempfile.mktemp(suffix=".yaml"); yaml.safe_dump({"beats": [{"type": "nope"}]}, open(p, "w"))
        with self.assertRaises(compose.StoryboardError): compose.load_storyboard(p)
    def test_faces_overlap(self):
        f = compose.Faces(dict(step=.5, found_ratio=1, frames=[dict(t=1.0, boxes=[[100, 100, 200, 200]])]), 1080, 1920)
        self.assertTrue(f.overlaps((0, 150, 500, 200), 0.5, 1.5)); self.assertFalse(f.overlaps((0, 1000, 500, 200), 0.5, 1.5))

if __name__ == "__main__": unittest.main()

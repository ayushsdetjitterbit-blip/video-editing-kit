
# ======================================================= map source time -> clean time
_off, _a = [], 0.0
for s_, e_ in keep: _off.append(_a); _a += e_ - s_
def M(t):
    for (s_, e_), o in zip(keep, _off):
        if s_ - 1e-6 <= t <= e_ + 1e-6: return round(o + t - s_, 3)
    for (s_, e_), o in zip(keep, _off):
        if t < s_: return round(o, 3)
    return round(_a, 3)
scenes = []; events = []
def ev(kind, t, **k): events.append(dict(kind=kind, t=M(t) if k.pop("src", True) else t, **k))
GROUPS = []
def group(a, b):
    return
def _old_group(a, b):
    if GROUPS and M(a) - GROUPS[-1][1] < 0.9:          # back-to-back panels stay in one panel mode
        GROUPS[-1] = (GROUPS[-1][0], M(b)); events[:] = [e for e in events if not (e["kind"] == "panel_end" and e["t"] == GROUPS[-1][0] * 0 + e["t"] and e.get("last"))]
        for e in events:
            if e["kind"] == "panel_end" and e.get("last"): e["t"] = M(b)
        return
    GROUPS.append((M(a), M(b))); ev("panel", a); ev("panel_end", b, last=True)
def mk(sid, a, b): s = Scene(sid, M(a), M(b)); scenes.append(s); return s
BLUE, GREEN, ORANGE, RED, PURPLE = "#0A84FF", "#30D158", "#FF9F0A", "#FF453A", "#5E5CE6"

# ---- full-frame cards (face fills the screen, cards sit under the chin)
s = mk("opening", 0.45, 8.1)
s.full_card("hook", M(0.55), M(2.4), "heart", "#FF375F", "Period Pain", "Normal or a warning sign?"); ev("card", 0.55, hook=True)
s.full_card("sym", M(5.9), M(8.05), "pill", ORANGE, "Cramps · Back pain", "Common period symptoms"); ev("card", 5.9)
s = mk("name", 8.6, 11.2)
s.full_card("n", M(8.75), M(11.1), "user", PURPLE, "Dr. Amrata Jain", "Women's Health Education"); ev("card", 8.75)
s = mk("ayur", 71.3, 73.75)
s.full_card("a", M(71.4), M(73.65), "doc", ORANGE, "आयुर्वेद · Ayurveda", "कष्टार्तव · Kashta Artava"); ev("card", 71.4)
s = mk("dont", 84.55, 88.4)
s.fs("d", M(84.65), M(88.3), "d4863.mp4", "See a gynaecologist", "stetho", BLUE, "Don't ignore severe pain", "It is not always normal", pos="80%"); ev("broll", 84.65)

# ---- panel groups (presenter shrinks to the top, content below)
def tiles(s, tid, a, b, L, R, ta, tb):
    sid = s.id
    html = (f'<div id="{sid}-{tid}" class="pcard glass" style="background:rgba(245,245,247,.0);border:none;box-shadow:none;backdrop-filter:none">'
      f'<div id="{sid}-{tid}L" class="tile" style="left:12px;background:linear-gradient(160deg,{L[1]},{L[2]});box-shadow:0 20px 50px {L[3]}">' + ICON[L[0]].replace('<svg ', '<svg style="width:130px;height:130px" ') + f'<div class="tt" style="font-size:{L[5] if len(L)>5 else 56}px">{L[4]}</div><div class="ts">{L[6] if len(L)>6 else ""}</div></div>'
      f'<div id="{sid}-{tid}R" class="tile" style="right:12px;background:linear-gradient(160deg,{R[1]},{R[2]});box-shadow:0 20px 50px {R[3]}">' + ICON[R[0]].replace('<svg ', '<svg style="width:130px;height:130px" ') + f'<div class="tt" style="font-size:{R[5] if len(R)>5 else 56}px">{R[4]}</div><div class="ts">{R[6] if len(R)>6 else ""}</div></div></div>')
    s.html.append(html)
    s.js += [f'tl.fromTo("#{sid}-{tid}", {{opacity:0, y:100}}, {{opacity:1, y:0, duration:.5, ease:"expo.out"}}, {s.L(M(a))});',
             f'tl.fromTo("#{sid}-{tid}L", {{opacity:0, x:-120, scale:.9}}, {{opacity:1, x:0, scale:1, duration:.55, ease:"expo.out"}}, {s.L(M(ta))});',
             f'tl.fromTo("#{sid}-{tid}R", {{opacity:0, x:120, scale:.9}}, {{opacity:1, x:0, scale:1, duration:.55, ease:"expo.out"}}, {s.L(M(tb))});',
             f'tl.to("#{sid}-{tid}", {{opacity:0, y:40, duration:.3, ease:"power3.in"}}, {s.L(M(b) - 0.3)});', f'tl.set("#{sid}-{tid}", {{opacity:0}}, {s.L(M(b))});']
    ev("card", a); ev("vs_right", tb)

s = mk("g1", 11.5, 18.0)
s.fs("fs", M(11.55), M(14.35), "m33383.mp4", "Period pain", "heart", "#FF375F", "Period pain", "Cramps · mood · tiredness"); ev("broll", 11.55)
tiles(s, "t", 14.4, 17.9, ("stetho", "#0A84FF", "#0B4FA8", "rgba(10,132,255,.35)", "Medical<br>Science", 52, "Modern view"), ("doc", "#FF9F0A", "#B35F00", "rgba(255,159,10,.35)", "Ayurveda<br>आयुर्वेद", 52, "Traditional view"), 14.54, 15.76)

s = mk("g2", 18.9, 25.3)
term = ('<div id="g2-c" class="pcard glass"><div style="position:absolute;left:44px;top:30px;font-weight:700;font-size:36px;color:rgba(235,235,245,.6)">Medical term for painful periods</div>'
        '<div id="g2-term" style="position:absolute;left:44px;top:92px;font-weight:900;font-size:92px;letter-spacing:-.03em;color:#FF9F0A;white-space:nowrap">Dysmenorrhea</div>'
        '<div style="position:absolute;left:44px;top:214px;font-weight:600;font-size:40px;color:rgba(235,235,245,.78)">Painful menstruation · पीरियड्स का दर्द</div>'
        '<div id="g2-p1" style="position:absolute;left:44px;top:312px;height:88px;padding:0 34px;border-radius:44px;background:rgba(10,132,255,.22);border:2px solid #0A84FF;display:flex;align-items:center;font-weight:800;font-size:44px">Type 1 · Primary</div>'
        '<div id="g2-p2" style="position:absolute;right:44px;top:312px;height:88px;padding:0 34px;border-radius:44px;background:rgba(255,159,10,.22);border:2px solid #FF9F0A;display:flex;align-items:center;font-weight:800;font-size:44px">Type 2 · Secondary</div></div>')
s.html.append(term); s.enter_exit("g2-c", M(19.0), M(25.2), dy=110, scale=.94)
s.js += [f'tl.fromTo("#g2-term", {{opacity:0, y:30, filter:"blur(10px)"}}, {{opacity:1, y:0, filter:"blur(0px)", duration:.6, ease:"expo.out"}}, {s.L(M(20.9))});',
         f'tl.fromTo("#g2-p1", {{opacity:0, scale:.8}}, {{opacity:1, scale:1, duration:.5, ease:"back.out(2)"}}, {s.L(M(23.4))});',
         f'tl.fromTo("#g2-p2", {{opacity:0, scale:.8}}, {{opacity:1, scale:1, duration:.5, ease:"back.out(2)"}}, {s.L(M(24.1))});']
ev("card", 19.0); ev("tick", 20.9); ev("tick", 23.4)

s = mk("g3", 25.35, 54.4)
tiles(s, "t", 25.45, 29.6, ("check", "#0A84FF", "#0B4FA8", "rgba(10,132,255,.35)", "Primary", 64, "Dysmenorrhea"), ("warn", "#FF9F0A", "#B35F00", "rgba(255,159,10,.35)", "Secondary", 64, "Dysmenorrhea"), 25.83, 27.27)
s.checklist("a", M(29.8), M(36.4), "Primary dysmenorrhea", "#64D2FF", [(M(31.4), "Happens during periods"), (M(33.9), "Pain & cramps")], "check", BLUE, BLUE); ev("card", 29.8); ev("tick", 31.4); ev("tick", 33.9)
s.fs("us", M(36.5), M(43.8), "m6061.mp4", "Uterus · normal", "heart", "#FF375F", "No sign of disease", "Primary pain is normal"); ev("broll", 36.5)
s.checklist("b", M(43.9), M(54.3), "Why it happens", "#64D2FF", [(M(44.1), "Not severe"), (M(46.6), "Prostaglandin chemicals ↑"), (M(50.5), "Uterus contractions")], "check", BLUE, BLUE); ev("card", 43.9)
for t in (44.1, 46.6, 50.5): ev("tick", t)

s = mk("g4", 54.5, 71.2)
s.checklist("s", M(54.7), M(71.1), "Secondary dysmenorrhea", "#FFB340", [(M(58.0), "Internal condition"), (M(62.4), "Fibroid · गांठ"), (M(64.5), "Uterine muscle changes"), (M(70.0), "Pain may increase")], "warn", ORANGE, ORANGE); ev("card", 54.7)
for t in (58.0, 62.4, 64.5, 70.0): ev("warn", t)
s.fs("fs", M(57.95), M(60.35), "m24658.mp4", "Internal condition", "warn", ORANGE, "Internal condition", "Pain from an underlying cause"); ev("broll", 57.95)

s = mk("g5", 73.85, 84.7)
s.fs("av", M(73.95), M(77.95), "br_herbal_oil.mp4", "Ayurveda · आयुर्वेद", "doc", ORANGE, "अपान वायु", "Apana Vata · plays an important role"); ev("broll", 73.95); ev("tick", 76.95)
s.checklist("f", M(78.5), M(84.6), "Painful periods when", "#FFB340", [(M(78.9), "आर्तव flow is disturbed"), (M(81.1), "Normal flow becomes difficult"), (M(82.9), "Pain is felt")], "warn", ORANGE, ORANGE); ev("card", 78.5)
for t in (78.9, 81.1, 82.9): ev("warn", t)

s = mk("g6", 88.4, 93.78)
fol = ('<div id="g6-c" class="pcard glass" style="background:rgba(250,250,252,.96);border:1.5px solid rgba(0,0,0,.06)">'
       '<div style="position:absolute;left:44px;top:26px;font-weight:800;font-size:46px;color:#1d1d1f">Women\'s Health</div>'
       '<div style="position:absolute;left:44px;top:92px;font-weight:600;font-size:32px;color:#86868b">Follow for more health education</div>'
       '<div id="g6-row" style="position:absolute;left:36px;right:36px;top:168px;height:150px;border-radius:44px;background:#fff;border:2px solid rgba(0,0,0,.08);box-shadow:0 8px 30px rgba(0,0,0,.08);display:flex;align-items:center;gap:26px;padding:0 24px">'
       '<div style="flex:none;width:100px;height:100px;border-radius:50px;background:linear-gradient(145deg,#FF9F0A,#FF375F);color:#fff;font-weight:900;font-size:50px;display:flex;align-items:center;justify-content:center">A</div>'
       '<div style="flex:1"><div style="font-weight:800;font-size:46px;color:#1d1d1f">Dr. Amrata Jain</div><div style="font-weight:600;font-size:30px;color:#86868b">Women\'s Health Education</div></div>'
       '<div id="g6-btn" style="flex:none;height:84px;padding:0 44px;border-radius:42px;background:#0A84FF;color:#fff;font-weight:800;font-size:40px;display:flex;align-items:center;justify-content:center;min-width:220px"><span id="g6-bt">Follow</span></div></div>'
       '<div id="g6-ty" style="position:absolute;left:0;right:0;top:340px;text-align:center;font-weight:900;font-size:56px;color:#1d1d1f;opacity:0">Thank you 🙏</div></div>')
s.html.append(fol); s.enter_exit("g6-c", M(88.5), DUR - 0.03, dy=120, scale=.94)
s.js += [f'tl.to("#g6-btn", {{scale:.9, duration:.12, ease:"power2.in"}}, {s.L(M(92.4))});', f'tl.to("#g6-btn", {{scale:1, backgroundColor:"#30D158", duration:.35, ease:"back.out(3)"}}, {s.L(M(92.52))});',
         f'tl.call(() => {{ document.getElementById("g6-bt").textContent = "Following ✓"; }}, [], {s.L(M(92.5))});',
         f'tl.fromTo("#g6-ty", {{opacity:0, y:24}}, {{opacity:1, y:0, duration:.5, ease:"expo.out"}}, {s.L(M(92.85))});']
ev("cta", 88.5); ev("send", 92.4)
for sc in scenes: sc.write()

# ======================================================= CAPTIONS (anchored chunks, corrected Hinglish)
WIN_END = {0: 5.5, 1: 8.2, 2: 18.04, 3: 25.16, 4: 29.14, 5: 33.74, 6: 36.34, 7: 43.76, 8: 54.28, 9: 61.1, 10: 62.23, 11: 63.27, 12: 71.08, 13: 73.72, 14: 76.51, 15: 78.21, 16: 84.5, 17: 93.64}
CH = [(0.45,"Hello everyone,"),(1.29,"क्या आपको भी"),(2.29,"periods के दौरान"),(3.37,"पेट के निचले"),(4.39,"हिस्से में दर्द"),
 (5.84,"cramps या कमर"),(6.72,"में दर्द होता है?"),
 (8.48,"मैं हूँ Dr. Amrata Jain"),(9.96,"और आज हम"),(10.76,"बात करेंगे कि"),(11.72,"periods में pain"),(12.98,"क्या होता है"),(14.24,"और Medical Science"),(15.48,"और Ayurveda में"),(16.62,"इसे कैसे"),(17.14,"समझा गया है"),
 (18.65,"Medical Science में"),(19.77,"painful menstruation"),(20.93,"को Dysmenorrhea"),(22.39,"कहते हैं"),(23.09,"ये mainly दो types"),(24.53,"होता है"),
 (25.41,"First, Primary"),(26.39,"Dysmenorrhea"),(27.09,"और Secondary"),(28.41,"Dysmenorrhea"),
 (29.97,"Primary Dysmenorrhea"),(31.15,"इसमें periods"),(32.27,"के दौरान जो"),(33.11,"महिलाएं"),(33.87,"pain और cramps"),(35.17,"को feel करती हैं"),
 (36.44,"ये हमारे uterus"),(38.02,"या reproductive organ"),(39.62,"में कोई भी बीमारी"),(40.66,"का sign नहीं"),(41.18,"होता है"),(41.66,"ये pain normal"),(43.06,"होता है"),
 (43.86,"ये severe नहीं"),(44.78,"होता है,"),(45.3,"ये हमारे"),(46.48,"prostaglandin नाम"),(47.68,"के chemicals के"),(48.78,"बढ़ने से होता है,"),(49.92,"जिससे uterus में"),(51.0,"contractions होते हैं"),(52.18,"और हम pain"),(53.12,"को feel करते हैं"),
 (54.7,"Secondary Dysmenorrhea"),(56.3,"इसमें periods का"),(57.52,"दर्द किसी"),(58.28,"अंदरूनी बीमारी"),(59.62,"की वजह से होता है"),
 (60.41,"जैसे गर्भाशय में"),(62.36,"गांठ होना"),(63.42,"गर्भाशय की जो"),(64.46,"muscles होती हैं"),(65.58,"उनमें कोई"),(66.26,"changes होना"),(67.16,"इसकी वजह से"),(68.16,"दर्द होता है"),(69.06,"और ये दर्द"),(70.08,"बढ़ भी जाता है"),
 (71.34,"आयुर्वेद में इसे"),(72.2,"कष्टार्तव कहा"),(73.08,"जाता है"),(73.93,"इसमें मुख्य रूप से"),(75.31,"अपान वायु की"),(76.29,"दुष्टि को"),(76.91,"important माना गया है"),
 (78.42,"जिससे आर्तव के"),(79.82,"normal flow में"),(81.16,"difficulty होती है"),(82.54,"और हम pain"),(83.58,"को feel करते हैं"),
 (84.61,"तो periods के"),(85.53,"severe pain को"),(86.47,"normal समझकर"),(87.39,"ignore नहीं करें"),(88.39,"ऐसी ही Women Health"),(89.75,"से related information"),(90.95,"के लिए हमारे"),(91.73,"page को follow करें"),(92.83,"Thank you")]
raw = []
for k, (t0, txt) in enumerate(CH):
    words = txt.split(" ")
    nxt = CH[k + 1][0] if k + 1 < len(CH) else 93.7
    end = min(nxt, t0 + 0.30 * len(words) + 0.5)
    # last chunk of a window ends at window end (+pad), not at the next window start
    for we in WIN_END.values():
        if t0 < we <= nxt and we - t0 < end - t0 + 0.6: end = min(end, we + 0.05) if nxt - we > 0.1 else end
    L = [max(len(w), 2) for w in words]; tot = sum(L); acc = t0; st = []
    for w, l in zip(words, L): st.append(M(acc)); acc += (end - t0) * l / tot
    if len(words) > 4 or len(txt) > 26:
        m_ = len(words) // 2; raw += [(words[:m_], st[:m_], M(end)), (words[m_:], st[m_:], M(end))]
    else: raw.append((words, st, M(end)))
groups = []
for k, (words, st, e) in enumerate(raw):
    nxt = raw[k + 1][1][0] if k + 1 < len(raw) else DUR
    t1 = min(e + 0.05, nxt - 0.02) if nxt - e > 0.0 else e
    if t1 <= st[-1]: t1 = st[-1] + 0.3
    groups.append(dict(t0=round(max(0.08, st[0] - 0.05), 3), t1=round(min(t1, DUR - 0.06), 3), words=words, st=st))
gh, cjs = "", []
for k, g in enumerate(groups):
    gh += f'<div id="cg{k}" class="cg" data-text="{" ".join(g["words"])}">' + "".join(f'<span id="cw{k}_{j}" class="cw">{w}</span>' for j, w in enumerate(g["words"])) + '</div>\n'
    cjs.append(f'tl.fromTo("#cg{k}", {{opacity:0, y:14, filter:"blur(6px)"}}, {{opacity:1, y:0, filter:"blur(0px)", duration:.16, ease:"power3.out"}}, {g["t0"]});')
    for j, st in enumerate(g["st"]):
        cjs.append(f'tl.fromTo("#cw{k}_{j}", {{color:"rgba(255,255,255,.52)"}}, {{color:"rgba(255,255,255,1)", duration:.1, ease:"none"}}, {round(max(g["t0"], st - 0.02), 3)});')
    cjs.append(f'tl.to("#cg{k}", {{opacity:0, duration:.1, ease:"power2.in"}}, {round(g["t1"] - 0.1, 3)});')
    cjs.append(f'tl.set("#cg{k}", {{opacity:0, visibility:"hidden"}}, {g["t1"]});')

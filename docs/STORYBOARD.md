# Storyboard reference

`storyboard.yaml` is a list of beats. Every beat has `type`, a start (`at:` source seconds or `say: "words"` found in the transcript) and an end (`until:`, `until_say:` or `for:` seconds).
Anything that cannot be resolved stops the run with a message that says what to fix. Beats that would cover a face stop the run too.

| type | what it is | main fields | covers |
|---|---|---|---|
| `card` | lower-third card | `title`, `sub`, `icon`, `color`, `hook: true` (opening sound), optional `y` | slot below the chin; moves to a free slot automatically |
| `checklist` | list that ticks as you say each item (1-5 items) | `title`, `style: check|warn`, `items: [{at|say, text}]` | panel at y 1056 |
| `tiles` | two big tiles (e.g. Normal / Abnormal) | `left:{title,sub,icon,color,at}`, `right:{...}` | panel |
| `term` | big term + two chips | `small`, `term`, `sub`, `chips:[{text,color,at}]` | panel |
| `follow` | follow button animation + thank you | `name`, `handle`, `heading`, `button`, `done_text`, `thanks`, `click_at` | panel |
| `broll` | full-screen footage (face hidden on purpose) | `file` (in `assets/`), `label`, `title`, `sub`, `pos` (crop position, e.g. `80%`) | whole screen |
| `still` | full-screen designed still | `icon`, `title`, `sub`, `label`, `bg: [c1, c2]` | whole screen |

Icons: see `ICON` in `vek/compose.py` (star, heart, check, warn, user, doc, pill, stetho, bulb, cal, chart, mic, flame, wave, shield, lab, bubble, play, drop).
Rules enforced for you: presenter never moved or shrunk; top 168 px clear; captions at y 1530; two full-screen beats cannot overlap; panels need 1-5 items; B-roll files must exist.

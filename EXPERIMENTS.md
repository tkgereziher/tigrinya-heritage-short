# Experiments

Format: **hypothesis → change (one thing, seed fixed) → result → decision**, each with evidence
(runs.jsonl timestamps, file names, listener counts). An entry only counts once it has a measured result.

| # | Status | Question | Outcome in one line |
|---|---|---|---|
| E3 | done | Does the 2–2.5 words/s rule hold for Tigrinya TTS? | No: 1.3 words/s; budget in Ge'ez characters (5.5/s) |
| E3b | done | Does the style prompt change pace? | Lively is 25% faster than unhurried; film fits at 83.4 s |
| E4 | done | Can an LLM draft and condense a fable faithfully? | Structure yes; it cut the twist and the moral's bridge |
| E5 | done | Does a global style block stay global? | No: "greens" coloured the manes; scoped to the landscape |
| E6 | done | How many referenced characters fit in one keyframe? | References force prominence; background characters go in text |
| E7 | done | Is Workers AI klein deterministic per seed? | No: 29.7% of pixels differ; promote variant files |
| E8 | done | Which fix stops the S07 mispronunciation? | A: same words + "two distinct words" instruction, chosen by a native speaker |
| E9 | done (pending listeners) | Which ACE-Step candidate fits under the narration? | s11: its ending lands on the end card |
| E10 | planned | Does ratio-10 ducking pump compared with ratio 6? | `render.duck.ratio` 6 vs 10, 3 listeners |
| E11 | planned | Are Ken Burns stills nearly as watchable as Wan clips on a phone? | blind A/B, 5 people (needs Wan clips) |

---

## E3. Tigrinya TTS pace vs the 2–2.5 words/s rule of thumb (2026-11-25), measured
**Hypothesis:** the brief's guide (130–220 words for 60–90 s) holds for Tigrinya with Gemini 3.8 Flash TTS.
**Change:** none. Measured storyboard v1 lines S01–S05 (voice Kore, style "Read warmly, unhurriedly ... grandparent").
**Result:**

| shot | words | Ge'ez chars | audio s | words/s | chars/s |
|---|---|---|---|---|---|
| S01 | 12 | 52 | 8.6 | 1.40 | 6.0 |
| S02 | 13 | 59 | 11.6 | 1.12 | 5.1 |
| S03 | 10 | 43 | 8.6 | 1.16 | 5.0 |
| S04 | 13 | 52 | 9.1 | 1.43 | 5.7 |
| S05 | 13 | 62 | 11.0 | 1.18 | 5.6 |

That's **about 1.3 words/s, about half the rule of thumb**. Tigrinya words are long, since they carry
prefixes and suffixes, so *words* are the wrong unit. Characters are steadier (5.0–6.0/s). v1's 706 characters
projected to about 128 s of narration, plus shot padding of about 140 s, against a 90 s maximum.
**Decision:** budget narration in Ge'ez characters, not words: 5.5 chars/s, so about 70 s of narration is
about 400–470 characters. Storyboard v2 was condensed to 465 chars (see E4). Every shot carries `changed_by`.

## E4. LLM storyboard draft vs human review (2026-11-25), measured
**Hypothesis:** Gemini can draft a schema-valid storyboard that stays faithful to an original Tigrinya tale.
**Change:** `python film.py draft` from story/brief.md. The primary model returned 503, so gemini-3.6-flash wrote it.
Raw draft: `outputs/script/storyboard.draft.gemini-3.6-flash.json`.
**Result:** valid against the schema on the first try, with 10 shots, a reason for every shot, and the grass kept
green in every image prompt. Six problems needed a human:
1. it **dropped the twist** («እቲ ሳዕሪ ቀጠልያ ምዃኑስ ኣጸቢቐ እፈልጥ እየ»), the line the whole fable turns on;
2. it dropped the ending (the leopard understands and apologises);
3. it cut the funniest line («ዓይንኻ ድዩ ተበላሽዩ?»);
4. it **invented a voice name** ("Warm Elder Storyteller") that the TTS API doesn't have;
5. it **invented a decision** (`chosen_reason: "Placeholder score awaiting final stem mixing"`);
6. it left "Made with AI" off the end card, which the brief requires.
A second call condensed the narration to per-shot character budgets (`outputs/script/narration_condensed_proposal.json`),
706 → 430 chars. It met every budget, but cut the bridge line «መቕጻዕትኻ ግን ብዛዕባ ሳዕሪ ኣይኮነን», which leaves the
lesson in S11 without anything to follow from. It also dropped the apology, and changed S01 to the present tense.
Restored all three, giving 465 chars.
**Decision:** schema validation catches structure but not meaning. The LLM is good at structure and at cutting to
a budget, and bad at knowing *which* line carries the story. A human reads every narration line before TTS.

## E3b. Does the style prompt change TTS pace? (2026-11-25), measured
**Hypothesis:** a "lively storyteller" instruction speeds Tigrinya delivery enough to fit 90 s without cutting more text.
**Change:** style_prompt only. Same line (S10 v2, 70 chars), model, voice Kore. Script: `experiments/tts_pace.py`.
**Result:** unhurried 10.68 s (5.9 chars/s) vs lively **7.96 s (7.9 chars/s), 25% faster**. Files:
`outputs/experiments/tts_pace_S10_*.wav`. At full scale, all 12 v2 lines came to 66.7 s of narration and the radio cut
to **83.4 s**, inside the target. The unhurried style would have made about 95 s.
**Decision:** adopted the lively style. That changed every line's cache key, so all 12 lines regenerated (that's
what caching should do). Listener judgement of whether it sounds rushed is pending (user test 1).

## E5. The style block's colours leak into the characters (2026-11-25), measured
**Hypothesis:** a global style block ("rich vibrant greens and warm ochres") colours only the scene.
**Change:** none at first; looked at 12 reference sheets (`outputs/reference/contact_sheet.png`).
**Result:** false. Lion manes and donkey manes came out **green** in most variants. The model applied "greens"
to whatever it drew. Fix: scope the colour, "*lush green grass and foliage in the landscape, while every animal keeps
its natural coat colours*". Same seeds regenerated: manes back to natural colour, and the green moved into the grass.
Before/after: `outputs/experiments/style_leak_compare.png`. Side effect: the lion's crown got fainter.
**Decision:** style blocks describe *where* a colour goes. This matters doubly here, because the joke depends on
the grass, not the animals, being green.

## E6. How many referenced characters can one keyframe hold? (2026-11-25), measured
**Hypothesis:** FLUX.2 klein with up to 3 reference images can compose multi-character scenes as prompted.
**Change:** none at first; reviewed all 12 v1 keyframes (`outputs/experiments/keyframes_v1/contact_sheet.png`).
**Result:** 9/12 usable. Failures: **S03** (donkey + leopard refs) drew *two donkeys*; **S09** (3 characters) drew a
*lion–leopard hybrid*; **S10** ("smiling") gave the lion a *human face* and copied the reference sheet's two-panel layout.
Fixes, one shot at a time:
- S03: explicit left/right placement plus "one single illustrated scene, not a character sheet". Fixed in 1 try.
- S10: "a real lion's face ... mouth closed" instead of "smiling". Fixed in 1 try, crown restored.
- S09 took 3 tries. v2 (donkey + leopard refs) put the donkey *large in front* even though the prompt said "far, small".
  v3 passes **only the leopard reference** and describes the distant donkey in plain text, which gave the right
  composition. Seeds 109/110 then drew a second tail, and seed 111 was clean (`outputs/keyframes/variants/S09_sheet.png`).
**Decision:** a reference image tells klein "draw this animal prominently". Pass references only for characters in
the foreground, describe background characters in text, and never write "smiling" for an animal.

## E7. Is Workers AI FLUX.2 klein deterministic per seed? (2026-11-25), measured
**Hypothesis:** the same prompt + seed + reference reproduces the same keyframe (the brief's "fixed seed" assumption).
**Change:** regenerated S09 with the exact prompt, seed 111 and reference used for `variants/S09_111.png`.
**Result:** **no.** Mean absolute pixel difference 30/255, 29.7% of pixels differing by >30. The pose changed
(crouching → standing) and so did the light. A third re-roll with `--force` was different again
(`outputs/experiments/keyframes_v1/S09_seed111_reroll.png`).
**Decision:** on this provider a seed is a *hint*, not a guarantee. Two consequences in code: (1) a chosen
`--explore` variant is **promoted** (its file copied in), not re-rolled (`keyframes.run`); (2) reproducibility comes
from committing outputs plus the content-hash cache, not from seeds. Seed-fixed A/B comparisons on this provider need
several samples per arm.

## E8. Fixing a TTS mispronunciation without changing the words (2026-11-26), measured
**Hypothesis:** the merge of «ይካትዓኒ ኣሎ» into "ይካዓረኒሎ" (user test 1, viewer 2) can be fixed by (A) a delivery
instruction, (B) a different but equivalent construction «ይካትዓኒ እዩ ዘሎ», or (C) a synonym «ይከራኸረኒ ኣሎ».
**Change:** one variable per variant; same model (gemini-3.8-flash-tts), voice and base style
(`experiments/pronunciation.py` → `outputs/experiments/pron_S07_*.wav`). Lengths: A 6.3 s, B 6.0 s, C 6.0 s.
**Result:** a native Tigrinya speaker (me) chose **A**: the original words, pronounced as two distinct words. A
pronunciation fix didn't need a word change, only an instruction for that one line.
**Decision:** storyboard gained a per-shot `narration.style_extra` (schema + `narration.run`; it's part of the line's
cache key). The auditioned file was **promoted** as `outputs/narration/S07.wav` under the exact key the pipeline computes,
not re-rolled, because generative audio, like the images in E7, needn't reproduce the take that was approved.

## E9. Which score candidate fits under the narration? (2026-11-26), measured, listener check pending
**Hypothesis:** of 3 seeds of one caption (instrumental krar + masenqo, sparse, no lead melody, 76 bpm, A minor,
90 s), the one with the steadiest texture fits best under the voice.
**Change:** seed only (11, 22, 33); same caption and metadata. ACE-Step 1.5 turbo on a Kaggle T4: **32 s for all three**
(FAILURES.md F10–F12). Each was auditioned as the full film soundtrack, with narration ducked and mastered to −14 LUFS
(`experiments/audition_music.py` → `outputs/experiments/audition_score_s*.mp3`), and its structure read from a
spectrogram (`outputs/experiments/music_spectrograms.png`).
**Result:**

| seed | raw loudness | loudness range (LRA) | structure |
|---|---|---|---|
| s11 | −15.3 LUFS | 6.2 dB | busiest high plucking (5–45 s); **ends on a sustained chord ~80–84 s, then silence** |
| s22 | −17.6 LUFS | **5.0 dB** (steadiest) | darkest; a bright flourish at ~50 s (under S09); no ending, runs to 90 s |
| s33 | −15.4 LUFS | 6.2 dB | flourish at ~11 s; tail ~86 s |

The hypothesis predicted s22. But the brief's music guidance also asks for "a theme that returns near the end", and only
s11 has a written ending. Its final chord starts at about 80 s, and the end card starts at **79.4 s**. Ducking handles
the busier texture under each line.
**Decision:** `music.chosen = score_s11.wav`. The fade-out is now a storyboard setting (`render.music_fade_out_s`):
0.8 s instead of a hard-coded 3 s, so the fade doesn't swallow the chord. **This choice is made from measurements,
not from listening.** It is confirmed or overturned by the listeners in user test 2 (DESIGN.md §4), and if they
overturn it, swapping is one field in storyboard.json.

<!-- Template:
## En. <title> (date)
**Hypothesis:** ...
**Change:** ... (everything else fixed: model, seed, prompt)
**Result:** numbers + what people said; runs.jsonl ts ...
**Decision:** what changed in storyboard.json / code because of it (commit ...)
-->

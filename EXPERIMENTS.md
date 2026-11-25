# Experiments

Format: **hypothesis → change (one thing, seed fixed) → result → decision**, each with evidence
(runs.jsonl timestamps, file names, listener counts). The planned experiments below are the queue.
An entry only counts once it has a measured result.

| # | Status | Hypothesis | Change (one variable) | Evidence to collect |
|---|---|---|---|---|
| E1 | planned | Gemini 3.8 Flash TTS speaks Tigrinya intelligibly | Same probe line in ti / am / en (`film.py smoke`) | native-speaker rating 1–5 per file, latency from runs.jsonl |
| E2 | planned | A style instruction improves delivery more than switching voices | Voice fixed (Kore), style_prompt on vs off; then style fixed, Kore vs Charon | 3 listeners' preference, audio_s (pace) |
| E3 | planned | Tigrinya narration runs slower than the 2.2 words/s rule of thumb | Measure words / audio_s per line | timing.json + word counts → measured w/s |
| E4 | planned | Passing the approved reference image (klein `input_image_0`) beats text-only description for identity consistency | Same prompts and seeds, refs on vs off, shots S02/S05/S07 | blind same/different-person judgement from 3 people |
| E5 | planned | FLUX.2 klein follows composition prompts better than FLUX.1 schnell | `CF_IMAGE_MODEL` swap, same prompt and seed, 4 shots | prompt-adherence checklist per image, latency, neurons |
| E6 | planned | Motion-only Wan prompts flicker less than prompts that re-describe the subject | Same keyframe and seed, two prompts | visible morph/flicker count per clip, gpu_s |
| E7 | planned | 480p/81-frame drafts are good enough to judge a clip, at roughly a third of 720p's GPU time | 832×480 vs 1280×704, same seed | gpu_s per clip, side-by-side notes |
| E8 | planned | fp16 on T4 produces NaN/black frames for Wan 2.2 5B | `--dtype fp16` vs `bf16` | ok/fail in runs_gpu.jsonl, gpu_s |
| E9 | planned | A sparse caption with no lead instrument sits better under narration | 3 ACE-Step seeds × 2 captions, auditioned under the voice at low volume | listener choice and why → `music.chosen_reason` |
| E10 | planned | Ducking at ratio 6 / release 1500 ms sounds natural; ratio 10 pumps | `render.duck.ratio` 6 vs 10 | mix_report.json LUFS, 3 listeners |
| E11 | planned | Ken Burns stills are judged nearly as watchable as Wan clips on a phone | Blind A/B of 2 shots, 5 people | preference counts |

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

<!-- Template:
## En. <title> (date)
**Hypothesis:** ...
**Change:** ... (everything else fixed: model, seed, prompt)
**Result:** numbers + what people said; runs.jsonl ts ...
**Decision:** what changed in storyboard.json / code because of it (commit ...)
-->

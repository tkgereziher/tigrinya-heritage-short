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

<!-- Template:
## En. <title> (date)
**Hypothesis:** ...
**Change:** ... (everything else fixed: model, seed, prompt)
**Result:** numbers + what people said; runs.jsonl ts ...
**Decision:** what changed in storyboard.json / code because of it (commit ...)
-->

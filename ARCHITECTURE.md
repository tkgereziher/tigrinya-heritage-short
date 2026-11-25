# Architecture

## One contract, five stages

```
story/brief.md ──draft──▶ storyboard.json ◀── schema/storyboard.schema.json (validated before every run)
                               │
        ┌──────────────┬───────┼──────────────┬───────────────┐
        ▼              ▼       ▼              ▼               ▼
   narration       keyframes   (reference)   music          shots
   Gemini TTS      FLUX.2 klein  sheet first  ACE-Step 1.5   Wan 2.2 TI2V-5B  ─┐
   per-shot WAV    per-shot PNG              (Kaggle GPU)    (Kaggle GPU)      │ fallback:
        │              │                         │               │             │ Ken Burns
        └──────────────┴──────────┬──────────────┴───────────────┘◀────────────┘ (FFmpeg)
                                  ▼
                              assemble (FFmpeg)
             timeline from measured narration → picture concat + end card
             → voice + ducked score → -14 LUFS → burned EN subtitles
             → outputs/final/film_16x9.mp4, film_9x16.mp4
```

`storyboard.json` is the only thing stages share. Each stage reads it, writes only its own folder under
`outputs/`, and never edits the storyboard. Human decisions (which reference seed, which score candidate)
are recorded *in* the storyboard (`reference_seed`, `music.chosen` + `chosen_reason`), so the repo
explains itself.

| Stage | Code | Reads | Writes | Runs on |
|---|---|---|---|---|
| script | `pipeline/script.py` | `story/brief.md`, schema | `storyboard.draft.json` (human copies to `storyboard.json`) | Gemini API |
| narration | `pipeline/narration.py` | `shots[].narration.text`, `narration.voice/style_prompt` | `outputs/narration/Sxx.wav`, `timing.json` | Gemini API |
| reference | `pipeline/keyframes.py:reference` | `characters[]`, `style.block` | `outputs/reference/<char>_<seed>.png` | Cloudflare |
| keyframes | `pipeline/keyframes.py:run` | `shots[].image_prompt/seed`, characters, style, approved reference | `outputs/keyframes/Sxx.png` | Cloudflare |
| shots (video) | `kaggle/wan22_i2v.py` | keyframes, `shots[].motion` | `outputs/clips/Sxx.mp4` + `Sxx.json` sidecar | Kaggle T4 |
| music | `kaggle/acestep_music.py`, `pipeline/music.py` | `music.cues[]`, `music.chosen` | `outputs/music/candidates/*`, `score.wav` | Kaggle T4 / local |
| shots (render) | `pipeline/shots.py` | clips or keyframes, timeline | `outputs/shots/<ratio>/Sxx.mp4` | local FFmpeg |
| assemble | `pipeline/assemble.py`, `mix.py`, `timeline.py` | everything above | `outputs/final/*` | local FFmpeg |

`python film.py` runs validate → narration → keyframes → music → shots → assemble. The GPU stages are
deliberately *outside* the one command: a stranger without a GPU can still regenerate the film from the
committed keyframes/clips, and the GPU scripts are idempotent jobs you run when you want new clips.

## The schema and its extra checks

`schema/storyboard.schema.json` (Draft 2020-12) fixes types, ranges and required fields: 8–12 shots,
shot ids `S01`…, a `reason` for every shot, motion prompts separate from image prompts, a Ken Burns
`fallback` for every shot. `common.validate` adds what a schema cannot express: unique shot ids, shots
only reference defined characters, and the **consent gate**: a character with `real_person: true`
must carry a `consent_id` that appears as `consent_id: <id>` in ETHICS.md, or nothing runs.

## Timing: picture is cut to the voice

`timeline.build` reads the *measured* narration durations (`outputs/narration/timing.json`) and makes
each shot `max(duration_s, offset + narration + 0.6 s)`. So narration length drives the edit, the radio
cut and the final cut share one timeline, and changing one line re-times only that shot and the start
times after it.

## Caching

Every artefact has a key `<stage>/<item>` in `outputs/cache.json`, storing a hash of **all** the inputs
that produced it (`common.h`): model id, prompt as sent (including the style block and character
text), seed, voice, and the content hash of any upstream file. A stage skips an item when the file exists
and the stored hash matches; it prints `cached` or `regenerated` for every item.

Consequences:
- Edit one `image_prompt` → that keyframe regenerates → its hash changes → its rendered shot segments
  re-render → the final concat re-runs. Every other shot prints `cached`, and runs.jsonl gets exactly one
  new image call.
- Edit one narration line → one TTS call; that shot's duration may change, which changes only that
  shot's segment (duration is part of its key) and the final mix.
- Edit the style block → every keyframe regenerates (correctly, since every prompt changed).
- Wan clips are cached by a **sidecar** (`Sxx.json`) holding the keyframe hash and motion prompt they were
  made from. `shots.clip_for` uses a clip only if the sidecar matches the current keyframe and prompt;
  a stale clip is announced and replaced by Ken Burns until it is regenerated. So a stale clip can't end
  up in the film without anyone noticing.

`--force` ignores the cache; `--only S03,S07` limits a stage to some shots.

## Failure handling

| Failure | Handling |
|---|---|
| 429 quota / 5xx | `common.retry`: exponential backoff + jitter, 4 tries, honours "retry in Ns" hints |
| 4xx (bad request, auth, unsupported language) | raised as `Fatal`, not retried; logged with the error text |
| TTS request shape changed between model generations | one automatic retry with the legacy body (`narration._body`) |
| LLM returns invalid storyboard JSON | validation errors fed back for one repair attempt; raw output kept |
| No Wan clip / stale clip / GPU quota gone | Ken Burns over the keyframe (`shots.render`), always available |
| No keyframe yet | dark slate of the right length, so the timeline and radio cut still work |
| No score chosen yet | synthetic placeholder pad (`mix.PLACEHOLDER`) |
| fp16 overflow on T4 (black/NaN frames) | detected in `wan22_i2v.py`, logged as a failure; rerun with `--dtype bf16/fp32` |
| Kaggle session dies mid-batch | clips and log lines are written per shot, so a rerun resumes |

Every failure that reaches runs.jsonl has `ok: false` and the error text; `python film.py costs` lists
the last ten.

## Logging

`runs.jsonl`, one line per model call: `ts, stage, shot, provider, model, seed, params (full prompt),
latency_s, gpu_s, cost_usd (always 0, free tier), list_price_usd, ok, output, error`, plus stage
extras (TTS `audio_s` and token usage, image `neurons`). GPU jobs write `runs_gpu.jsonl` next to their
outputs on Kaggle; `python film.py ingest` merges them without duplicates. Secrets are read from `.env`
(git-ignored) and never logged.

## Audio chain

voice lines → placed at `narr_start` → normalised to −16 LUFS │ score → looped/trimmed, 1.5 s fade-in,
3 s fade-out → normalised to −24 LUFS │ `sidechaincompress` (threshold 0.02, ratio 6, attack 300 ms,
release 1500 ms; all in `render.duck`) │ mix → two-pass `loudnorm` to −14 LUFS, −1 dBTP. The measured
result is written to `outputs/final/work/mix_report.json`.

## Two aspect ratios from one set of images

Keyframes are square (1024²) with the subject centred (`keyframes.COMPOSE` is appended to every prompt).
`shots.cover` scales to fill and centre-crops, so 16:9 and 9:16 are both cut from the same picture.
Subtitles are written as ASS with `PlayRes` = output size; the vertical version sits above the bottom
22% that TikTok/Reels UI covers.

# Failures

What broke, what I tried, what fixed it. Newest at the bottom. Each entry links to evidence
(runs.jsonl lines with `ok: false`, commits, or files).

---

### F1. The Gemini docs and TTS request shape had moved (2026-11-25)
- **What happened:** The `ai.google.dev/gemini-api/docs/*` URLs now 301-redirect to `aistudio.google.com/docs/*`.
  The main TTS examples now use a new `/v1beta/interactions` endpoint. The `generateContent` examples for the
  current `gemini-3.8-flash-tts` set a single voice with `voiceConfig.voice` and the style with
  `speech_metadata.style`, where older models used `prebuiltVoiceConfig.voiceName` plus a style prefix in the
  prompt. Non-streaming audio now comes back as a complete WAV file, not raw PCM.
- **Tried / fixed:** `narration.py` sends the new shape and, on a 400, retries once with the legacy shape.
  `write_wav` accepts either a RIFF WAV or raw PCM. Model IDs live in `.env`, and `python film.py smoke`
  lists the models the key can actually see.
- **Lesson:** keep provider-specific request shapes in one function and expect them to change.

### F2. No Flash-Lite text model at the 3.8 version
- **What happened:** the brief mentions "Flash-Lite for bulk calls". The models page lists `gemini-3.8-flash`
  and `gemini-3.5-flash-lite`, but no `gemini-3.8-flash-lite`. Flash-Lite **TTS** also does not list Tigrinya.
- **Fixed:** text uses `gemini-3.8-flash`, TTS uses `gemini-3.8-flash-tts` (the one that lists Tigrinya).

### F3. Windows machine: no `make`, no FFmpeg
- **What happened:** the suggested `make film` does not exist on a stock Windows install, and FFmpeg was not
  installed.
- **Fixed:** the one command is `python film.py` (cross-platform). FFmpeg is being installed with
  `winget install Gyan.FFmpeg`. The pipeline checks for it and prints that install command if it's missing.

### F4. Local Python 3.14 vs ACE-Step's 3.11–3.12 requirement
- **What happened:** ACE-Step 1.5 supports Python 3.11–3.12. This machine has 3.14 and no GPU.
- **Fixed by design:** the GPU stages run as standalone scripts on Kaggle (`kaggle/`), with their own installs.
  The local pipeline needs only `requests`, `jsonschema` and `Pillow`.

### F5. gemini-3.8-flash returned 503 "high demand" on the first smoke test (2026-11-25)
- **What happened:** four attempts with exponential backoff (2 s, 5 s, 8 s) all returned HTTP 503, "This model is
  currently experiencing high demand". `gemini-flash-latest` also returned 503 a minute later. The
  ok:false lines are in runs.jsonl. TTS (`gemini-3.8-flash-tts`) and Cloudflare were fine at the same moment.
- **Tried:** 1) retries alone: not enough, since the overload lasted longer than the backoff window.
  2) probed the other text models my key lists: `gemini-3.5-flash` answered in 16 s.
- **Fixed:** `script.call` now walks a model chain (`GEMINI_TEXT_MODEL`, then `GEMINI_TEXT_FALLBACKS`,
  default `gemini-3.5-flash,gemini-2.5-flash`). Each model gets 3 tries, a 4xx stops immediately, and the
  log line records `fallback_from` so it's visible which model actually wrote the storyboard.
- **Lesson:** retries cover seconds-long blips; a fallback model covers a provider being overloaded for minutes.

### F6. TTS quota: 429 after 5 narration lines, with retryDelay 632 s (2026-11-25)
- **What happened:** after the 3 smoke-test probes, narration S01–S05 succeeded, then S06 returned HTTP 429
  "You exceeded your current quota". `error.details[].retryDelay` asked for a wait of **632 s**, so this is a
  window of roughly 10 minutes, not a per-minute cap. A probe a minute later succeeded, so it is a rolling limit.
  My retry parsed only "retry in Ns" from the message text, which was cut off at 300 chars, so it backed off for
  2–9 s, burned 3 attempts and crashed.
- **Tried:** 1) rotating TTS models like the text stage. Rejected: a different TTS model is a different narrator
  voice mid-film. 2) waiting out the window.
- **Fixed:** `http_check` reads `retryDelay` from the JSON error and passes it to `retry`, so the stage sleeps exactly
  as long as Google asks. Narration gets 6 tries. TTS calls are now treated as scarce: the pace experiment runs on
  one line before regenerating all 12.

### F7. My bug: a crash lost all narration timings (2026-11-25)
- **What happened:** `timing.json` was written only at the end of the narration stage, so the 429 crash in F6 lost the
  durations of the 5 finished lines. On a rerun, cached lines would also have counted as 0 s, and the radio
  cut rendered with an empty subtitle file, which made libass fail ("Unable to open subs.srt").
- **Fixed:** timing is written after every line; cached lines read their duration from the WAV header; `timeline.build`
  falls back to the WAV when timing.json is missing; radio and assembly skip the subtitle filter if there are no subtitles.
- **Lesson:** derived state (timing.json) should always be rebuildable from the artefacts (WAVs).

### F8. Gemini text calls: read timeout and 503s, again (2026-11-25)
- **What happened:** the narration-condensing call to `gemini-3.8-flash` hit a 300 s read timeout, then a 503.
- **Fixed by F5's chain:** it switched to `gemini-3.6-flash`, which answered. Every text call today has
  needed the fallback at least once (see runs.jsonl `stage: script`).

### F9. TTS daily cap: retryDelay 85,729 s after 23 calls (2026-11-25)
- **What happened:** regenerating all 12 lines in the lively style (E3b), S01–S10 succeeded and S11 got a 429 with
  `retryDelay` **85,729 s (about 23.8 h)**. That's the daily request cap for `gemini-3.8-flash-tts` on the free tier.
  runs.jsonl shows 23 successful TTS calls that day: smoke probes, the v1 lines, the pace experiment and the v2 lines.
  Every experiment spends the same budget the film needs.
- **Tried:** waiting would push the radio cut, and so user test 1, to tomorrow.
- **Worked around:** each Gemini model has its own quota, so S11–S12 were generated with
  `gemini-3.1-flash-tts-preview`, same voice name (Kore):
  `GEMINI_TTS_MODEL=gemini-3.1-flash-tts-preview python film.py narration --only S11,S12`.
  The model is part of each line's cache key, so after the reset a normal `python film.py narration` regenerates
  exactly S11 and S12 with 3.8 and leaves S01–S10 cached. That restores one consistent narrator.
- **Lesson:** budget TTS calls like money: probe on one line, then batch. And never let a 24 h `retryDelay` turn into a
  24 h sleep: `retry` now raises `Quota` at once when the requested wait is over 15 min (`MAX_WAIT_S`).

### F10. ACE-Step won't install on Kaggle: the image moved to Python 3.13 (2026-11-26)
- **What happened:** `pip install -e ACE-Step-1.5` → `ERROR: Package 'ace-step' requires a different Python:
  3.13.16 not in '<3.13,>=3.11'`. The script then failed with `ModuleNotFoundError: No module named 'acestep'`.
  I had flagged the 3.11–3.12 requirement for my *local* 3.14 (F4) and assumed Kaggle's image would be in range.
  It isn't anymore.
- **Tried:** 1) plain `pip install`, refused as above. 2) Rejected `--ignore-requires-python`: forcing an unsupported
  interpreter swaps a clear error now for unclear ones later.
- **Fixed:** an isolated Python 3.12 inside the notebook, the way ACE-Step's own README installs it:
  `pip install uv && cd ACE-Step-1.5 && uv python install 3.12 && uv sync --python 3.12`, then run the script with
  `ACE-Step-1.5/.venv/bin/python`. Kaggle's 3.13 is untouched. (kaggle/README.md updated.)
- **Lesson:** a hosted notebook's Python version is a moving dependency like any model ID. Check it
  (`python --version`) as the first cell, and give each tool its own environment.

### F11. ACE-Step import crash: Jupyter's matplotlib backend leaks into the venv (2026-11-26)
- **What happened:** with F10 fixed (Python 3.12.16, torch 2.10.0+cu128, `cuda True`), importing `acestep.handler`
  crashed deep in lightning → torchmetrics → matplotlib: `ValueError: Key backend:
  'module://matplotlib_inline.backend_inline' is not a valid value`. Kaggle's Jupyter exports `MPLBACKEND` for
  inline plots, and the separate uv venv doesn't have `matplotlib_inline`.
- **Fixed:** `acestep_music.py` sets `MPLBACKEND=Agg` before importing anything. This is a headless job, so it never
  needs a GUI backend.
- **Lesson:** an isolated venv isolates packages, not environment variables. Every subprocess inherits the
  notebook's env.

### F12. ACE-Step on a T4: all-NaN audio in fp16 + int8, and my script logged it as "ok" (2026-11-26)
- **What happened:** the model downloaded (28 files, about 10 GB in 27 s) and loaded in 42 s. ACE-Step detected the
  pre-Ampere T4 and switched to float16 with eager attention, and my `--offload` flag also applied int8 weight
  quantization. Diffusion took 9.2 s for 3 × 90 s (1.14 s/step), then decoding failed: `Generation produced NaN or
  Inf latents (shape=[3, 2250, 64], dtype=torch.float16, nan=432000)`. Every value was NaN.
- **My bug:** `generate_music` catches its own exception and returns an empty result. My script took that as
  success and logged `ok: true, output: []` ("score: ok [] in 18s"). A failed generation would have shown up in
  COSTS.md as a successful call.
- **Also:** the planner LM never ran (`llm_initialized=False`). I asked for `acestep-5Hz-lm-0.6B`, but the
  auto-download fetches `acestep-5Hz-lm-1.7B`.
- **Changed two things at once:** set `ACESTEP_DTYPE=float32` (the fix ACE-Step's error message names) *and*
  dropped int8 (now opt-in via `--int8`). CPU offload was kept, the planner LM was off, and an empty result now raises.
- **Result:** success. 3 candidates × 90 s in **32 s** (diffusion 9.1 s, VAE decode about 12 s, peak VRAM 5.7 GB of 14.6).
  But the log still says `Dtype: torch.float16`: ACE-Step ignored `ACESTEP_DTYPE` in this version. **The fix was
  removing int8**: fp16 alone works on a T4, and fp16 + int8 weight quantization produced NaNs. My first explanation
  (fp16) was wrong. I only know because the log printed the dtype it actually used.
- **Lesson:** I changed two variables in one run, so the success didn't tell me which one mattered; only the
  library's own log line did. Read the "what I actually ran with" lines, not just the exit status. And never trust a
  library's return value as success without checking the payload.

### F13. My quota probes spent the quota they were checking (2026-11-26)
- **What happened:** at 03:19 EAT I checked whether the TTS daily cap had reset by sending a one-word request. It
  returned 200, so I started the S07 pronunciation experiment, and its first call got a 429 with `retryDelay` 16,800 s
  (4.7 h). The probe had used the only free slot in the rolling window. Over the session, 3 such probes were
  real `generateContent` calls on a budget of about 23 per day.
- **What worked:** the F9 fail-fast. `retry` raised `Quota` after one attempt instead of sleeping 4.7 h.
- **Fixed:** no more probes. The job is scheduled from the `retryDelay` Google returns (about 08:05 EAT) and spends its
  calls only on work: 3 pronunciation variants plus S11–S12.
- **Lesson:** on a quota this small, checking the quota costs quota. Trust the provider's `retryDelay`.

<!-- Template for new entries:
### Fn. <short title> (date)
- **What happened:** exact error / symptom, with the runs.jsonl ts if it was a model call
- **Tried:** 1) ... 2) ...
- **Fixed / worked around:** ...
- **Lesson:** ...
-->

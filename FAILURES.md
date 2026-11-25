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

<!-- Template for new entries:
### Fn. <short title> (date)
- **What happened:** exact error / symptom, with the runs.jsonl ts if it was a model call
- **Tried:** 1) ... 2) ...
- **Fixed / worked around:** ...
- **Lesson:** ...
-->

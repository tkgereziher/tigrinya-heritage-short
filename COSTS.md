# Costs and latency

**Actual spend: $0.** List-price equivalent of everything generated: **about $0.05**. The binding limits were the
Gemini TTS daily cap and the text model's availability, never money. Every number below comes from `runs.jsonl`
(`python film.py costs`, saved in `outputs/costs_table.md`), as of 26 Nov 2026, the submission day.

## Measured, by stage

| Stage | Model | Calls (ok) | Median latency | Max latency | GPU min | List-price USD |
|---|---|---|---|---|---|---|
| Script draft + condensing | gemini-3.8-flash → gemini-3.6-flash | 6 (3) | 81–139 s | 318 s | – | not estimated |
| Narration | gemini-3.8-flash-tts | 26 (23) | 4.7 s | 59.6 s (includes a retry wait) | – | not estimated |
| Narration stopgap (F9) | gemini-3.1-flash-tts-preview | 2 (2) | 5.6 s | 5.6 s | – | not estimated |
| TTS experiments (pace, pronunciation) | gemini-3.8-flash-tts | 5 (5) | 5.0 s | 5.6 s | – | not estimated |
| Smoke tests | Gemini TTS, models.list, FLUX.2 klein | 10 (10) | 1.4–10.2 s | 10.2 s | – | ≈0 |
| Reference sheets + keyframes + variants | FLUX.2 klein 4B (Workers AI) | 36 (36) | 8.9 s | 107 s (includes a connection retry) | – | 0.043 |
| Score, 3 candidates × 90 s | ACE-Step 1.5 turbo (Kaggle T4) | 1 batch (1) | 32.5 s | 32.5 s | 0.5 | 0.003 |
| Assembly, both ratios | FFmpeg (laptop, no GPU) | – | 129–179 s per full render | – | – | 0 |
| **Total** | | **86 (80)** | | | **0.5** | **≈ 0.05** |

Not in the log: 7 TTS requests sent by hand outside `log_call` (quota checks and model probes, FAILURES.md F13), so
TTS requests over the two days total about **43**.

## How list prices were computed

- **Workers AI images:** neurons per image from Cloudflare's published rates (FLUX.2 klein about 26 neurons per 512²
  output tile plus 5.4 per reference tile), at $0.011 per 1,000 neurons beyond the free allowance. 38 images used
  **3,912 neurons**: 39% of one day's free 10,000. Per image: about 104–120 neurons, about $0.0012.
- **Kaggle GPU:** priced at an on-demand T4 rate of $0.35/GPU-hour (`pipeline/costs.py: GPU_HOUR_USD`). The music
  run is 32.5 s, about $0.003. Model download (about 10 GB in 27 s) and load (42 s first time, 9 s after) are
  setup, not counted as generation.
- **Gemini text and TTS:** not estimated. These ran on the free tier, and I didn't record token counts in a way I
  trust for a price. The constraint that mattered was the request cap, below.

## Free tiers as found (25–26 Nov 2026)

| Provider | What I measured | Where it bit |
|---|---|---|
| Gemini TTS (3.8 Flash) | About **23 requests per rolling day**; 429 with `retryDelay` 632 s after a burst, then 85,729 s at the daily cap | Shaped the whole schedule (F6, F9, F13, F14) |
| Gemini text (3.8 Flash) | Frequent **503 "high demand"**; 3 of 4 calls failed; 3.6 Flash answered every time | Model fallback chain (F5, F8) |
| Cloudflare Workers AI | 10,000 neurons/day, reset 00:00 UTC; never hit | none |
| Kaggle | T4 (14.6 GB usable); Python 3.13 image; about 30 GPU h/week | 0.5 of about 1,800 GPU minutes used (F10–F12) |

## Throughput

- **Narration:** 4.7 s median per line for about 3.6–8.8 s of audio, so TTS runs faster than real time.
  The limit is the request count, not speed.
- **Images:** about 9 s each, so all 12 keyframes take under 2 minutes.
- **Music:** about 11 s of GPU per 90-second candidate when batched (3 in 32.5 s).
- **Final film:** 82.7 s, rendered in 2–3 min on a laptop with no GPU.

## Frontier comparison

None: no frontier lane (Omni Flash, Nano Banana, Lyria 3.5) was available to this cohort, so there is no
open-vs-frontier cost or quality comparison.

## Video (Wan 2.2)

Not run for this cut. Every shot uses the Ken Burns fallback, which costs nothing (FFmpeg). `kaggle/wan22_i2v.py`
and its notes are ready; its GPU cost would be logged the same way as the music.

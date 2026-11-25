# Costs and latency

**Actual spend: $0.** Every number below is measured from runs.jsonl. Regenerate the table with
`python film.py costs` and paste the output here. List prices are what the same calls would cost on paid tiers.

## Free tiers as found (2026-11-25)

| Provider | What I found | Notes |
|---|---|---|
| Gemini API (AI Studio) | Free tier available from Ethiopia | Record the RPM/RPD limits you hit, as 429s in runs.jsonl |
| Cloudflare Workers AI | 10,000 neurons/day, reset 00:00 UTC; paid $0.011 / 1k neurons | klein-4B ≈ 26 neurons per 512² output tile (≈104 per 1024² image, ~95 images/day); schnell ≈ 58 per 1024² |
| Kaggle | ~30 GPU h/week, 2× T4, phone verification | Sessions time out; scripts save per shot |

## Measured, by stage

<!-- paste `python film.py costs` output here -->

## GPU minutes and list-price equivalent

GPU time is priced at an on-demand T4 rate ($0.35/GPU-h) for comparison (`pipeline/costs.py: GPU_HOUR_USD`).

| Stage | Items | GPU min total | GPU min / item | List-price USD |
|---|---|---|---|---|
| Wan 2.2 clips (832×480, 81 frames, 30 steps) | | | | |
| ACE-Step candidates | | | | |

## Frontier comparison

No frontier lane access this cohort (Omni Flash / Nano Banana / Lyria 3.5 need paid billing). If
access opens, compare one shot here: cost, latency and blind preference.

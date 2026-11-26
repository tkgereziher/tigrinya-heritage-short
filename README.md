# ንጉስ ኣራዊት ኣያ ኣንበሳ: a Tigrinya fable, made by a storyboard-to-film pipeline

An 84-second animated short of a Tigrinya fable (a donkey says the grass is blue, a leopard says it's green, and
the lion king's verdict has a twist). It is narrated in Tigrinya with English subtitles and an original score,
and generated from one file, `storyboard.json`, by free hosted APIs, open weights on a free GPU, and FFmpeg.
Change one line of the storyboard, rerun, and only that shot regenerates.

## The film

| | |
|---|---|
| Length | 84.4 s (12 shots + a 5 s end card), cut to the measured voice track |
| Exports | `outputs/final/film_9x16.mp4` (1080×1920) and `film_16x9.mp4` (1920×1080), H.264/AAC, 24 fps |
| Sound | Tigrinya narration (Gemini 3.8 Flash TTS, voice Kore), ACE-Step score ducked under it, −14.1 LUFS / −1.0 dBTP |
| Subtitles | English, burned in, inside the vertical safe area; also `outputs/final/subtitles_en.srt` |
| Pictures | FLUX.2 klein keyframes conditioned on character reference sheets; Ken Burns motion in FFmpeg |
| Labelling | End card: the moral in Tigrinya and English, "Made with AI" and the models used; fictional characters |
| Links | Film, walkthrough and post: *to add* |

## Run it

```bash
git clone https://github.com/tkgereziher/tigrinya-heritage-short.git && cd tigrinya-heritage-short
python -m venv .venv && .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt                     # requests, jsonschema, Pillow
cp .env.example .env                                # GEMINI_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
python film.py                                      # validate → narration → keyframes → music → shots → assemble
```

Needs Python 3.11+ (developed on 3.14, Windows 11) and FFmpeg on PATH (Windows: `winget install Gyan.FFmpeg`).

**Reproducibility.** Every generated file and the content-hash cache (`outputs/cache.json`) are committed. On a
clean clone every stage prints `cached` and only FFmpeg runs, so no API calls are made and no keys are needed to
rebuild the film. `--force` regenerates everything, and gives a *similar* film, not the same one: the image API is
not deterministic per seed (EXPERIMENTS.md E7). The committed outputs are what make the film reproducible.

## Commands

| Command | What it does |
|---|---|
| `python film.py` | The whole pipeline; each item prints `cached` or `regenerated` |
| `python film.py smoke` | One call per provider, latency logged, TTS probe in Tigrinya / Amharic / English |
| `python film.py draft` | Gemini drafts `storyboard.draft.json` from `story/brief.md` (validated; a human reviews and copies) |
| `python film.py validate` | JSON Schema + consent gate (a real person needs a consent record in ETHICS.md) |
| `python film.py radio` | Checkpoint 1: narration + placeholder music on black, with subtitles |
| `python film.py reference --variants 4` | Character sheet options; pin one with `characters[].reference_seed` |
| `python film.py keyframes [--explore N]` | One keyframe per shot, or N seed variants (a chosen variant is promoted as a file) |
| `python film.py narration \| music \| shots \| assemble` | Individual stages |
| `python film.py status` | Per shot: narration, keyframe, picture source (wan / kenburns / slate) |
| `python film.py costs` | Calls, latency, GPU minutes, list price per stage, from `runs.jsonl` |
| `python film.py ingest` | Merge Kaggle GPU logs into `runs.jsonl` |

Flags: `--only S03,S07`, `--force`, `--ratio 9x16`, `--draft` (half resolution).

### GPU stages (Kaggle T4)

These are notebook jobs, because they need a GPU and the one command must work without one. Step-by-step
instructions are in [kaggle/README.md](kaggle/README.md). Kaggle's image runs Python 3.13, so ACE-Step runs in its
own Python 3.12 environment made with `uv`.

- **Music:** `kaggle/acestep_music.py` (ACE-Step 1.5 turbo) made 3 candidates × 90 s in **32 s** on a T4. Seed 11
  was chosen and recorded in `music.chosen` / `chosen_reason` (EXPERIMENTS.md E9).
- **Video:** `kaggle/wan22_i2v.py` (Wan 2.2 TI2V-5B) writes clips with a sidecar recording the keyframe hash and
  motion prompt. The shots stage uses a clip only if the sidecar matches the current storyboard. **No Wan clips
  are in this cut:** every shot uses the Ken Burns fallback, which the shots stage renders whenever no valid
  clip exists.

## Regenerate one shot (the walkthrough demo)

1. In `storyboard.json`, add a sentence to S04's `image_prompt`, e.g. "A small blue butterfly rests on the grass by his hoof."
2. Run `python film.py`.
3. The log shows `[keyframes] S04 regenerated` and every other item `cached` (no TTS calls), then S04's segment
   re-rendered in both ratios. `runs.jsonl` gains exactly one line: one image call for S04.

## Results in numbers

| | Measured |
|---|---|
| Spend | **$0** (list-price equivalent about $0.05: images $0.043, T4 time about $0.003) |
| Model calls logged | 73 (69 ok), plus 7 TTS requests sent by hand outside the log (FAILURES.md F13) |
| Narration pace | Tigrinya at **1.3 words/s**, about half the usual rule of thumb; budgeted in Ge'ez characters (E3) |
| Hardest limit | Gemini TTS free tier: **about 23 calls/day**, with a rolling window (F6, F9, F13) |
| Image latency | 8.9 s median per FLUX.2 klein image; 3,912 of 10,000 daily free neurons used |
| Full render | 158–179 s for both ratios on a laptop |

What broke and how it was handled: [FAILURES.md](FAILURES.md) (F1–F13). What was tested and what it changed:
[EXPERIMENTS.md](EXPERIMENTS.md). What the audience said and what changed: [DESIGN.md](DESIGN.md).

## Repo map

| Path | Purpose |
|---|---|
| `storyboard.json` | The contract: shots, reasons, prompts, seeds, narration, music cues, end card (v3) |
| `schema/` | JSON Schema, validated before every run |
| `story/brief.md` | The fable's original Tigrinya text, audience and look, input to `draft` |
| `pipeline/` | One module per stage, plus `common.py` (cache, retries, logging) and `mix.py` (ducking, loudness) |
| `kaggle/` | GPU jobs: ACE-Step 1.5 score, Wan 2.2 image-to-video |
| `experiments/` | Scripts behind EXPERIMENTS.md (TTS pace, pronunciation, music audition) |
| `runs.jsonl` | One line per model call: model, params, seed, latency, cost, ok/error |
| `outputs/` | Every generated artefact plus the cache, kept for inspection |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Stages, contracts, caching, failure handling |
| [DESIGN.md](DESIGN.md) · [EXPERIMENTS.md](EXPERIMENTS.md) · [FAILURES.md](FAILURES.md) · [COSTS.md](COSTS.md) · [ETHICS.md](ETHICS.md) | Evidence |

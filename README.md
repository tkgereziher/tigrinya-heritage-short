# Heritage Short: a storyboard-to-film pipeline

A 60–90 second short narrated in Tigrinya with English subtitles and an original score, generated
from one file, `storyboard.json`, by a pipeline of free hosted APIs, open-weight models on a free GPU,
and FFmpeg. Change one line of the storyboard, rerun, and only that shot regenerates.

## Run it

```bash
git clone <this repo> && cd <repo>
python -m venv .venv && .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt                     # requests, jsonschema, Pillow
cp .env.example .env                                # add GEMINI_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
python film.py                                      # validate → narration → keyframes → music → shots → assemble
```

Needs Python 3.11+ and FFmpeg on PATH (Windows: `winget install Gyan.FFmpeg`). Output:
`outputs/final/film_9x16.mp4`, `film_16x9.mp4` and `subtitles_en.srt`.

Generated media is committed, so on a clean clone every stage prints `cached` and only FFmpeg runs.
No API calls are made and no keys are needed to rebuild the edit. Add `--force` to regenerate everything.

## Commands

| Command | What it does |
|---|---|
| `python film.py smoke` | One call per provider, latency logged, TTS probe in Tigrinya/Amharic/English |
| `python film.py draft` | Gemini drafts `storyboard.draft.json` from `story/brief.md` (validated; you review and copy) |
| `python film.py validate` | Schema + consent gate |
| `python film.py radio` | Checkpoint 1: narration + placeholder music on black, with subtitles |
| `python film.py reference --variants 4` | Character sheet options; pin one with `characters[].reference_seed` |
| `python film.py keyframes [--explore 4]` | One keyframe per shot (or N seed variants to choose from) |
| `python film.py shots \| music \| assemble` | Individual stages |
| `python film.py status` | Per shot: narration / keyframe / picture source (wan, kenburns, slate) |
| `python film.py costs` | Latency, GPU minutes and list price per stage, from runs.jsonl |
| `python film.py ingest` | Merge Kaggle GPU logs into runs.jsonl |

Flags: `--only S03,S07`, `--force`, `--ratio 9x16`, `--draft` (half resolution).

### GPU stages (Kaggle, 2× T4)

Video and music run as notebook jobs, because they need a GPU and the one command must work without one:

```bash
# in a Kaggle notebook with GPU T4 x2 and internet on; full instructions in each script's header
python kaggle/wan22_i2v.py --shard 0/2 --device cuda:0 & python kaggle/wan22_i2v.py --shard 1/2 --device cuda:1
python kaggle/acestep_music.py --acestep ACE-Step-1.5
```

Download `outputs/clips/` and `outputs/music/candidates/` into the local repo, run `python film.py ingest`,
set `music.chosen`, then run `python film.py`. A shot without a valid clip falls back to a Ken Burns move
over its keyframe, so the film always renders.

## Regenerate one shot (the walkthrough demo)

1. Edit `shots[2].image_prompt` (or one `narration.text`) in `storyboard.json`.
2. Run `python film.py`.
3. The log shows `S03 regenerated` and every other shot `cached`. `runs.jsonl` gains exactly one new line.

## What it costs

$0. Measured latency and list-price equivalents are in [COSTS.md](COSTS.md).

## Repo map

| Path | Purpose |
|---|---|
| `storyboard.json` | The contract: shots, durations, prompts, seeds, narration, music cues |
| `schema/` | JSON Schema, validated before every run |
| `pipeline/` | One module per stage + `common.py` (cache, retries, logging) |
| `kaggle/` | GPU jobs: Wan 2.2 image-to-video, ACE-Step 1.5 score |
| `runs.jsonl` | One line per model call: model, params, seed, latency, cost |
| `outputs/` | Every generated artefact, kept for inspection |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Stages, contracts, caching, failure handling |
| [DESIGN.md](DESIGN.md) | Audience, intent, the two user tests and what they changed |
| [EXPERIMENTS.md](EXPERIMENTS.md) · [FAILURES.md](FAILURES.md) · [COSTS.md](COSTS.md) · [ETHICS.md](ETHICS.md) | Evidence |

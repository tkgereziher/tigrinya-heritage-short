#!/usr/bin/env python
"""One command for the whole pipeline.

    python film.py                 # validate -> narration -> keyframes -> shots -> music -> assemble
    python film.py validate        # check storyboard.json against the schema (+ consent gate)
    python film.py smoke           # call each provider once, log latency, probe the TTS language
    python film.py draft           # Gemini drafts storyboard.draft.json from story/brief.md
    python film.py narration       # TTS, one file per shot
    python film.py radio           # checkpoint 1: narration + placeholder music on black
    python film.py reference       # character reference sheet options (pick one via reference_seed)
    python film.py keyframes [--explore N]
    python film.py shots | music | assemble
    python film.py costs           # measured cost/latency table from runs.jsonl
    python film.py ingest          # merge Kaggle GPU logs (outputs/clips, outputs/music) into runs.jsonl
    python film.py status          # what's cached, what's stale

Options: --only S03,S07 (limit to shots)  --force (ignore cache)  --ratio 9x16  --draft
Every stage skips work whose inputs haven't changed (outputs/cache.json).
"""
from __future__ import annotations

import argparse
import json
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pipeline import (assemble, costs, keyframes, music, narration, radio, script, shots,
                      smoke)
from pipeline.common import D_CLIPS, D_KEY, D_NARR, load_storyboard, say


def status(sb: dict) -> None:
    print(f"{sb['title']}  v{sb['version']}  language={sb['language']['code']}  shots={len(sb['shots'])}")
    for s in sb["shots"]:
        n = (D_NARR / f"{s['id']}.wav").exists()
        k = (D_KEY / f"{s['id']}.png").exists()
        c = shots.clip_for(s) is not None
        src = "wan" if c else ("kenburns" if k else "slate")
        print(f"  {s['id']}  narration={'y' if n else '-'}  keyframe={'y' if k else '-'}  picture={src}"
              f"   {s['reason'][:60]}")
    print(f"music.chosen = {sb['music'].get('chosen')}")


def ingest() -> None:
    """Merge GPU logs written on Kaggle into runs.jsonl (idempotent)."""
    from pipeline.common import D_MUSIC, RUNS
    have = set(RUNS.read_text(encoding="utf-8").splitlines()) if RUNS.exists() else set()
    added = 0
    for src in [D_CLIPS / "runs_gpu.jsonl", D_MUSIC / "candidates" / "runs_gpu.jsonl"]:
        if not src.exists():
            continue
        with RUNS.open("a", encoding="utf-8") as f:
            for line in src.read_text(encoding="utf-8").splitlines():
                if line.strip() and line not in have:
                    f.write(line + "\n")
                    have.add(line)
                    added += 1
    print(f"ingested {added} GPU log line(s) into runs.jsonl")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", nargs="?", default="all")
    ap.add_argument("--only", help="comma-separated shot ids")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--ratio", choices=["16x9", "9x16"])
    ap.add_argument("--draft", action="store_true", help="half-resolution render")
    ap.add_argument("--explore", type=int, default=0, help="keyframes: N seed variants per shot")
    ap.add_argument("--variants", type=int, default=4, help="reference: options per character")
    a = ap.parse_args()
    only = a.only.split(",") if a.only else None
    ratios = [a.ratio] if a.ratio else None

    if a.stage == "smoke":
        return smoke.run()
    if a.stage == "draft":
        return script.draft()
    if a.stage == "costs":
        return costs.run()
    if a.stage == "ingest":
        return ingest()

    sb = load_storyboard()
    if a.draft:
        sb.setdefault("render", {})["draft"] = True
    t0 = time.time()
    if a.stage == "validate":
        print(f"storyboard.json is valid: {len(sb['shots'])} shots, v{sb['version']}")
    elif a.stage == "status":
        status(sb)
    elif a.stage == "narration":
        narration.run(sb, only, a.force)
    elif a.stage == "radio":
        narration.run(sb, only, a.force)
        radio.run(sb)
    elif a.stage == "reference":
        keyframes.reference(sb, a.variants, a.force)
    elif a.stage == "keyframes":
        keyframes.run(sb, only, a.force, a.explore)
    elif a.stage == "shots":
        shots.run(sb, only, a.force, ratios)
    elif a.stage == "music":
        music.run(sb, a.force)
    elif a.stage in ("assemble", "all"):
        if a.stage == "all":
            say("film", f"storyboard valid: {len(sb['shots'])} shots")
            narration.run(sb, only, a.force)
            keyframes.run(sb, only, a.force)
            music.run(sb, a.force)
        assemble.run(sb, only, a.force, ratios)
    else:
        ap.error(f"unknown stage {a.stage!r}")
    say("film", f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()

"""Stage: music. Candidates are generated on a GPU by kaggle/acestep_music.py into
outputs/music/candidates/. This local stage promotes the one named in
storyboard.music.chosen to outputs/music/score.wav. With no choice yet, the edit
uses a synthetic placeholder pad (see mix.py), so the pipeline always completes.
"""
from __future__ import annotations

from .common import D_MUSIC, Cache, file_hash, run_ff, say

STAGE = "music"


def run(sb: dict, force: bool = False) -> None:
    cands = D_MUSIC / "candidates"
    cands.mkdir(parents=True, exist_ok=True)
    found = sorted(p.name for p in cands.iterdir() if p.suffix.lower() in {".wav", ".mp3", ".flac"})
    say(STAGE, f"{len(found)} candidate(s): {', '.join(found) or 'none yet - run kaggle/acestep_music.py'}")
    chosen = sb["music"].get("chosen")
    score = D_MUSIC / "score.wav"
    if not chosen:
        if score.exists():
            score.unlink()
        say(STAGE, "no score chosen -> placeholder pad")
        return
    src = cands / chosen
    if not src.exists():
        raise SystemExit(f"music.chosen = {chosen!r} but {src} does not exist")
    cache = Cache()
    digest = file_hash(src)
    if not force and cache.fresh(f"{STAGE}/score", digest, score):
        say(STAGE, f"score cached ({chosen})")
        return
    run_ff(["-i", str(src), "-ar", "48000", "-ac", "2", str(score)])
    cache.put(f"{STAGE}/score", digest)
    say(STAGE, f"score = {chosen}  ({sb['music'].get('chosen_reason', 'no reason recorded yet')})")

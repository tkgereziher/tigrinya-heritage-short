"""The edit decision list, computed from the storyboard and the measured narration.

Picture is cut to the voice: each shot lasts at least its storyboard duration, and is
extended so its narration line (plus a short breath) fits inside it.
"""
from __future__ import annotations

import json
import textwrap
import wave
from pathlib import Path

from .common import D_NARR

TAIL_S = 0.6          # breath after a line before the cut
DEFAULT_OFFSET = 0.4  # breath before a line
MAX_CHARS = 40        # subtitle line length
MAX_LINES = 2


def build(sb: dict) -> list[dict]:
    tp = D_NARR / "timing.json"
    timing = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else {}
    t = 0.0
    edl = []
    for s in sb["shots"]:
        narr = float(timing.get(s["id"], 0.0))
        wav = D_NARR / f"{s['id']}.wav"
        if not narr and wav.exists() and s["narration"]["text"].strip():
            # timing.json is a convenience; the WAV on disk is the truth.
            with wave.open(str(wav), "rb") as w:
                narr = w.getnframes() / w.getframerate()
        off = s["narration"].get("offset_s", DEFAULT_OFFSET) if narr else 0.0
        dur = max(float(s["duration_s"]), off + narr + TAIL_S if narr else 0.0)
        edl.append({"id": s["id"], "start": round(t, 3), "dur": round(dur, 3),
                    "narr_start": round(t + off, 3), "narr_dur": narr,
                    "english": s["narration"]["english"]})
        t += dur
    return edl


def total(sb: dict, edl: list[dict]) -> float:
    return edl[-1]["start"] + edl[-1]["dur"] + sb["end_card"]["duration_s"]


def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    hh, ms = divmod(ms, 3_600_000)
    mm, ms = divmod(ms, 60_000)
    ss, ms = divmod(ms, 1000)
    return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"


def subtitles(edl: list[dict], path: Path) -> None:
    """English SRT. Long lines are split into <=2x40-char cards, timed in proportion
    to their length across the narration line they translate."""
    n, out = 1, []
    for e in edl:
        text = " ".join(e["english"].split())
        if not text or not e["narr_dur"]:
            continue
        lines = textwrap.wrap(text, MAX_CHARS)
        cards = [lines[i:i + MAX_LINES] for i in range(0, len(lines), MAX_LINES)]
        weights = [sum(len(l) for l in c) for c in cards]
        t = e["narr_start"]
        span = e["narr_dur"] + 0.3
        for c, w in zip(cards, weights):
            d = span * w / sum(weights)
            out.append(f"{n}\n{_ts(t)} --> {_ts(t + d)}\n" + "\n".join(c) + "\n")
            n += 1
            t += d
    path.write_text("\n".join(out), encoding="utf-8")


def report(sb: dict, edl: list[dict]) -> str:
    rows = [f"{e['id']}  start {e['start']:6.2f}s  dur {e['dur']:5.2f}s  narration {e['narr_dur']:5.2f}s"
            for e in edl]
    rows.append(f"TOTAL with end card: {total(sb, edl):.1f}s (target 60-90s)")
    return "\n".join(rows)

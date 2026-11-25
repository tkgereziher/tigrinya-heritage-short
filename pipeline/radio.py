"""Checkpoint 1: the radio cut. Narration over placeholder music on a black screen,
with English subtitles so testers who don't speak the narration language can follow.
"""
from __future__ import annotations

import shutil

from . import mix, timeline
from .common import D_RADIO, run_ff, say

STAGE = "radio"


def run(sb: dict) -> None:
    D_RADIO.mkdir(parents=True, exist_ok=True)
    edl = timeline.build(sb)
    total = timeline.total(sb, edl)
    say(STAGE, "timeline:\n" + timeline.report(sb, edl))
    audio = mix.soundtrack(sb, edl, total, D_RADIO / "work", placeholder_music=True)
    timeline.subtitles(edl, D_RADIO / "subs.srt")
    shutil.copy(audio, D_RADIO / "radio_cut.wav")
    style = "FontName=Arial,FontSize=20,Outline=2,Shadow=0,MarginV=40"
    has_subs = (D_RADIO / "subs.srt").read_text(encoding="utf-8").strip() != ""
    vf = f"subtitles=subs.srt:force_style='{style}'" if has_subs else "null"
    run_ff(["-f", "lavfi", "-i", f"color=c=black:s=1280x720:r=24:d={total:.3f}",
            "-i", "radio_cut.wav",
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "radio_cut.mp4"], cwd=D_RADIO)
    say(STAGE, f"wrote outputs/radio/radio_cut.mp4 ({total:.1f}s)")

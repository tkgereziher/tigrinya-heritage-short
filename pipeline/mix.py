"""Soundtrack: narration spine, score ducked under it, final loudness pass.

voice  -> placed at each shot's narration start, normalised to voice_lufs
music  -> chosen ACE-Step score (or a synthetic placeholder pad), looped/trimmed,
          faded, normalised to music_lufs
duck   -> sidechaincompress: the voice drives a compressor on the music
master -> two-pass loudnorm to target_lufs / true peak
"""
from __future__ import annotations

import json
from pathlib import Path

from .common import D_MUSIC, D_NARR, duration, loudness, normalise, render_cfg, run_ff, say

STAGE = "mix"
PLACEHOLDER = ("aevalsrc=exprs='0.05*sin(2*PI*110*t)*(1+0.3*sin(2*PI*0.13*t))"
               "+0.035*sin(2*PI*164.81*t)*(1+0.3*sin(2*PI*0.21*t))"
               "+0.025*sin(2*PI*220*t)*(1+0.4*sin(2*PI*0.08*t))':s=48000:c=stereo")


def voice_track(edl: list[dict], total_s: float, work: Path) -> Path | None:
    clips = [(e, D_NARR / f"{e['id']}.wav") for e in edl if e["narr_dur"] > 0]
    clips = [(e, p) for e, p in clips if p.exists()]
    if not clips:
        return None
    args, chains = [], []
    for i, (e, p) in enumerate(clips):
        args += ["-i", str(p)]
        ms = int(e["narr_start"] * 1000)
        chains.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
    mix_in = "".join(f"[a{i}]" for i in range(len(clips)))
    fc = ";".join(chains) + f";{mix_in}amix=inputs={len(clips)}:normalize=0:duration=longest,apad,atrim=0:{total_s:.3f}[v]"
    raw = work / "voice_raw.wav"
    run_ff([*args, "-filter_complex", fc, "-map", "[v]", "-ar", "48000", str(raw)])
    return raw


def music_track(sb: dict, total_s: float, work: Path, placeholder: bool,
                score: Path | None = None) -> tuple[Path, str]:
    score = score or D_MUSIC / "score.wav"
    fade_out = max(total_s - 3.0, 0)
    raw = work / "music_raw.wav"
    if score.exists() and not placeholder:
        src = "score"
        run_ff(["-stream_loop", "-1", "-i", str(score), "-t", f"{total_s:.3f}",
                "-af", f"afade=t=in:d=1.5,afade=t=out:st={fade_out:.3f}:d=3", "-ar", "48000", "-ac", "2", str(raw)])
    else:
        src = "placeholder"
        run_ff(["-f", "lavfi", "-i", PLACEHOLDER, "-t", f"{total_s:.3f}",
                "-af", f"afade=t=in:d=1.5,afade=t=out:st={fade_out:.3f}:d=3", str(raw)])
    return raw, src


def soundtrack(sb: dict, edl: list[dict], total_s: float, work: Path, placeholder_music: bool = False,
               score: Path | None = None) -> Path:
    cfg = render_cfg(sb)
    work.mkdir(parents=True, exist_ok=True)
    music_raw, src = music_track(sb, total_s, work, placeholder_music, score)
    music = work / "music_norm.wav"
    normalise(music_raw, music, cfg["music_lufs"])

    voice_raw = voice_track(edl, total_s, work)
    mixed = work / "mix_raw.wav"
    d = cfg["duck"]
    if voice_raw:
        voice = work / "voice_norm.wav"
        normalise(voice_raw, voice, cfg["voice_lufs"])
        fc = (f"[1:a]asplit=2[sc][v];"
              f"[0:a][sc]sidechaincompress=threshold={d['threshold']}:ratio={d['ratio']}:"
              f"attack={d['attack_ms']}:release={d['release_ms']}[m];"
              f"[m][v]amix=inputs=2:normalize=0:duration=first[out]")
        run_ff(["-i", str(music), "-i", str(voice), "-filter_complex", fc, "-map", "[out]", str(mixed)])
    else:
        mixed = music

    master = work / "soundtrack.wav"
    normalise(mixed, master, cfg["target_lufs"], cfg["true_peak_db"])
    m = loudness(master)
    rep = {"music_source": src, "duck": d, "voice_lufs": cfg["voice_lufs"], "music_lufs": cfg["music_lufs"],
           "measured_I": m.get("input_i"), "measured_TP": m.get("input_tp"), "duration_s": round(duration(master), 2)}
    (work / "mix_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    say(STAGE, f"soundtrack {rep['duration_s']}s  music={src}  {rep['measured_I']} LUFS  TP {rep['measured_TP']} dB")
    return master

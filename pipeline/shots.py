"""Stage: moving shots -> outputs/shots/<ratio>/<shot>.mp4 (picture only).

For each shot the source is, in order of preference:
  1. a Wan 2.2 clip in outputs/clips/<shot>.mp4 whose sidecar <shot>.json matches the
     *current* keyframe hash and motion prompt (made by kaggle/wan22_i2v.py), or
  2. a Ken Burns move over the keyframe (FFmpeg zoompan) - the always-available fallback.

A stale clip (its keyframe or motion prompt changed since it was generated) is ignored
with a warning, so the film never shows a clip that no longer matches the storyboard.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import timeline
from .common import (D_CLIPS, D_KEY, D_SHOTS, RATIOS, Cache, duration, file_hash, h,
                     render_cfg, run_ff, say, selected_shots)

STAGE = "shots"
KB = 0.12  # Ken Burns zoom amount


def clip_for(shot: dict) -> Path | None:
    """Return the Wan clip for this shot if it exists and matches the current inputs."""
    clip, meta = D_CLIPS / f"{shot['id']}.mp4", D_CLIPS / f"{shot['id']}.json"
    key = D_KEY / f"{shot['id']}.png"
    if not shot["motion"].get("use_video", True) or not clip.exists():
        return None
    if not meta.exists() or not key.exists():
        say(STAGE, f"{shot['id']} clip has no sidecar; ignoring it")
        return None
    m = json.loads(meta.read_text(encoding="utf-8"))
    if m.get("keyframe_hash") != file_hash(key) or m.get("motion_prompt") != shot["motion"]["prompt"]:
        say(STAGE, f"{shot['id']} clip is STALE (keyframe or motion prompt changed) -> Ken Burns until regenerated on Kaggle")
        return None
    return clip


def zoompan(move: str, frames: int, w: int, hgt: int, fps: int) -> str:
    n = max(frames - 1, 1)
    p = f"(on/{n})"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    z, x, y = {
        "push_in":   (f"1+{KB}*{p}", cx, cy),
        "pull_out":  (f"{1 + KB}-{KB}*{p}", cx, cy),
        "pan_left":  (f"{1 + KB}", f"(iw-iw/zoom)*(1-{p})", cy),
        "pan_right": (f"{1 + KB}", f"(iw-iw/zoom)*{p}", cy),
        "pan_up":    (f"{1 + KB}", cx, f"(ih-ih/zoom)*(1-{p})"),
        "pan_down":  (f"{1 + KB}", cx, f"(ih-ih/zoom)*{p}"),
        "static":    ("1.04", cx, cy),
    }[move]
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{hgt}:fps={fps}"


def cover(w: int, hgt: int, mult: int = 1) -> str:
    """Scale to fill WxH (times mult) and centre-crop: works for any source aspect."""
    W, H = w * mult, hgt * mult
    return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"


def render(shot: dict, dur: float, ratio: str, cfg: dict, out: Path) -> str:
    w, hgt = RATIOS[ratio]
    if cfg["draft"]:
        w, hgt = w // 2, hgt // 2
    fps = cfg["fps"]
    frames = int(round(dur * fps))
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an"]
    clip = clip_for(shot)
    if clip:
        ts = shot["motion"].get("trim_start_s", 0.3)
        te = shot["motion"].get("trim_end_s", 0.3)
        usable = max(duration(clip) - ts - te, 0.5)
        hold = max(dur - usable, 0)
        vf = (f"trim=start={ts}:duration={min(usable, dur):.3f},setpts=PTS-STARTPTS,fps={fps},{cover(w, hgt)},"
              f"tpad=stop_mode=clone:stop_duration={hold:.3f},setsar=1")
        run_ff(["-i", str(clip), "-vf", vf, "-frames:v", str(frames), *enc, str(out)])
        return "wan"
    key = D_KEY / f"{shot['id']}.png"
    if not key.exists():
        # No keyframe yet: a dark slate keeps the timeline intact.
        run_ff(["-f", "lavfi", "-i", f"color=c=0x101010:s={w}x{hgt}:r={fps}:d={dur:.3f}", *enc, str(out)])
        return "slate"
    vf = f"{cover(w, hgt, 2)},{zoompan(shot['motion']['fallback'], frames, w, hgt, fps)},setsar=1"
    run_ff(["-loop", "1", "-i", str(key), "-vf", vf, "-frames:v", str(frames), *enc, str(out)])
    return "kenburns"


def source_digest(shot: dict) -> str:
    clip = clip_for(shot)
    if clip:
        return "wan:" + file_hash(clip)
    key = D_KEY / f"{shot['id']}.png"
    return "kb:" + (file_hash(key) if key.exists() else "none")


def run(sb: dict, only: list[str] | None = None, force: bool = False,
        ratios: list[str] | None = None) -> dict[str, list[Path]]:
    cache, cfg = Cache(), render_cfg(sb)
    edl = {e["id"]: e for e in timeline.build(sb)}
    want = {s["id"] for s in selected_shots(sb, only)}
    result = {}
    for ratio in ratios or list(RATIOS):
        d = D_SHOTS / ratio
        d.mkdir(parents=True, exist_ok=True)
        paths = []
        for shot in sb["shots"]:
            sid, out = shot["id"], d / f"{shot['id']}.mp4"
            paths.append(out)
            if sid not in want and out.exists():
                continue
            dur = edl[sid]["dur"]
            digest = h(source_digest(shot), dur, shot["motion"], ratio, cfg["fps"], cfg["draft"])
            if not force and cache.fresh(f"{STAGE}/{ratio}/{sid}", digest, out):
                say(STAGE, f"{ratio} {sid} cached")
                continue
            kind = render(shot, dur, ratio, cfg, out)
            cache.put(f"{STAGE}/{ratio}/{sid}", digest)
            say(STAGE, f"{ratio} {sid} regenerated ({kind}, {dur:.2f}s)")
        result[ratio] = paths
    return result

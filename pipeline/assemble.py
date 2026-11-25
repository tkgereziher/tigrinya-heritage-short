"""Stage: assembly -> outputs/final/film_16x9.mp4 and film_9x16.mp4

picture  = shot segments + AI end card, concatenated
sound    = narration spine + ducked score, normalised to -14 LUFS / -1 dBTP (mix.py)
subtitle = English, burned in, positioned inside each ratio's safe area
FFmpeg is deterministic: same inputs, same film.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import mix, shots, timeline
from .common import D_FINAL, RATIOS, render_cfg, run_ff, say

STAGE = "assemble"

FONTS_LATIN = ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "/System/Library/Fonts/Supplemental/Arial.ttf"]
FONTS_ETHIOPIC = ["C:/Windows/Fonts/ebrima.ttf", "C:/Windows/Fonts/nyala.ttf",
                  "/usr/share/fonts/truetype/noto/NotoSansEthiopic-Regular.ttf",
                  "/usr/share/fonts/opentype/noto/NotoSansEthiopic-Regular.ttf"]


def _font(text: str, size: int):
    from PIL import ImageFont
    ethiopic = any("\u1200" <= ch <= "\u139f" for ch in text)
    for f in (FONTS_ETHIOPIC if ethiopic else []) + FONTS_LATIN:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def end_card_png(sb: dict, w: int, hgt: int, path: Path) -> None:
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, hgt), (12, 10, 8))
    d = ImageDraw.Draw(im)
    lines = sb["end_card"]["lines"]
    sizes = [int(min(w, hgt) * (0.06 if i == 0 else 0.035)) for i in range(len(lines))]
    gaps = int(min(w, hgt) * 0.03)
    heights = [s * 1.25 for s in sizes]
    y = (hgt - sum(heights) - gaps * (len(lines) - 1)) / 2
    for line, s, lh in zip(lines, sizes, heights):
        f = _font(line, s)
        tw = d.textlength(line, font=f)
        d.text(((w - tw) / 2, y), line, font=f, fill=(236, 226, 208) if s == sizes[0] else (190, 180, 165))
        y += lh + gaps
    im.save(path)


def ass_subs(edl: list[dict], path: Path, w: int, hgt: int) -> None:
    """Write subtitles as ASS with PlayRes = the output size, so font size and margins
    are in real pixels for each ratio. Vertical keeps text above the bottom ~22% that
    platform buttons and captions cover."""
    vertical = hgt > w
    fs = int(hgt * (0.027 if vertical else 0.048))
    mv = int(hgt * (0.22 if vertical else 0.07))
    ml = int(w * 0.07)
    srt_tmp = path.with_suffix(".srt")
    timeline.subtitles(edl, srt_tmp)
    events = []
    for block in srt_tmp.read_text(encoding="utf-8").strip().split("\n\n"):
        rows = block.splitlines()
        if len(rows) < 3:
            continue
        a, b = rows[1].split(" --> ")
        conv = lambda t: f"{int(t[:2])}:{t[3:5]}:{t[6:8]}.{t[9:11]}"
        text = r"\N".join(rows[2:])
        events.append(f"Dialogue: 0,{conv(a)},{conv(b)},Default,,0,0,0,,{text}")
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\nWrapStyle: 0\nScaledBorderAndShadow: yes\n"
        f"PlayResX: {w}\nPlayResY: {hgt}\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,Arial,{fs},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,"
        f"{max(2, fs // 18)},0,2,{ml},{ml},{mv},1\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + "\n".join(events) + "\n",
        encoding="utf-8")


def run(sb: dict, only: list[str] | None = None, force: bool = False, ratios: list[str] | None = None) -> None:
    cfg = render_cfg(sb)
    D_FINAL.mkdir(parents=True, exist_ok=True)
    edl = timeline.build(sb)
    total = timeline.total(sb, edl)
    say(STAGE, "timeline:\n" + timeline.report(sb, edl))
    segments = shots.run(sb, only=only, force=force, ratios=ratios)
    audio = mix.soundtrack(sb, edl, total, D_FINAL / "work")
    timeline.subtitles(edl, D_FINAL / "subtitles_en.srt")
    fps, ec = cfg["fps"], sb["end_card"]["duration_s"]

    for ratio, paths in segments.items():
        w, hgt = RATIOS[ratio]
        if cfg["draft"]:
            w, hgt = w // 2, hgt // 2
        work = D_FINAL / "work" / ratio
        work.mkdir(parents=True, exist_ok=True)
        # End card segment
        end_card_png(sb, w, hgt, work / "end_card.png")
        run_ff(["-loop", "1", "-i", "end_card.png", "-vf", f"fps={fps},fade=t=in:d=0.5,format=yuv420p",
                "-t", f"{ec}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-an", "end_card.mp4"], cwd=work)
        # Concatenate picture
        lst = work / "concat.txt"
        lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in paths) +
                       f"file '{(work / 'end_card.mp4').resolve().as_posix()}'\n", encoding="utf-8")
        run_ff(["-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "picture.mp4"], cwd=work)
        # Subtitles + sound + final encode
        ass_subs(edl, work / "subs.ass", w, hgt)
        shutil.copy(audio, work / "soundtrack.wav")
        out = f"film_{ratio}.mp4"
        subs = "ass=subs.ass," if "Dialogue:" in (work / "subs.ass").read_text(encoding="utf-8") else ""
        run_ff(["-i", "picture.mp4", "-i", "soundtrack.wav",
                "-vf", f"fade=t=in:d=0.8,{subs}fps={fps},format=yuv420p",
                "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-movflags", "+faststart", "-t", f"{total:.3f}", out], cwd=work)
        shutil.move(work / out, D_FINAL / out)
        say(STAGE, f"wrote outputs/final/{out}  ({total:.1f}s, {w}x{hgt})")

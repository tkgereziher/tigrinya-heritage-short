"""E9: audition the ACE-Step score candidates the way the film will use them.

For each outputs/music/candidates/*.wav, render the full soundtrack (narration + this candidate,
normalised, ducked, mastered to -14 LUFS) to outputs/experiments/audition_<name>.mp3, and print
measurements that bear on "does it sit under a voice": loudness range of the raw track (LRA, dB;
lower = steadier texture) and how much the music level drops under the voice after ducking.

    python experiments/audition_music.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import mix, timeline  # noqa: E402
from pipeline.common import D_MUSIC, OUT, ffmpeg_bin, load_storyboard, run_ff  # noqa: E402


def lra(path: Path) -> dict:
    p = subprocess.run([ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = p.stderr[p.stderr.rfind("Summary:"):]
    get = lambda k: float(re.search(rf"{k}:\s+(-?[0-9.]+)", tail).group(1))
    return {"I": get("I"), "LRA": get("LRA")}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sb = load_storyboard()
    edl = timeline.build(sb)
    total = timeline.total(sb, edl)
    d = OUT / "experiments"
    d.mkdir(parents=True, exist_ok=True)
    res = {}
    for cand in sorted((D_MUSIC / "candidates").glob("*.wav")):
        work = d / f"audition_{cand.stem}"
        track = mix.soundtrack(sb, edl, total, work, score=cand)
        mp3 = d / f"audition_{cand.stem}.mp3"
        run_ff(["-i", str(track), "-c:a", "libmp3lame", "-b:a", "192k", str(mp3)])
        raw = lra(cand)
        rep = json.loads((work / "mix_report.json").read_text(encoding="utf-8"))
        res[cand.name] = {"raw_I_LUFS": raw["I"], "raw_LRA_dB": raw["LRA"], "final_I": rep["measured_I"],
                          "final_TP": rep["measured_TP"], "audition": str(mp3.relative_to(OUT.parent))}
        print(f"{cand.name}: raw {raw['I']:.1f} LUFS, LRA {raw['LRA']:.1f} dB -> {mp3.name} "
              f"({rep['measured_I']} LUFS, TP {rep['measured_TP']})")
    (d / "audition_music.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

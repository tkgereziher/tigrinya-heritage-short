"""E3b: does the style prompt change Tigrinya TTS pace? One variable: style_prompt.
Same model, voice and line. Writes outputs/experiments/tts_pace_<label>.wav and logs to runs.jsonl.

    python experiments/tts_pace.py S10
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import narration  # noqa: E402
from pipeline.common import OUT, load_env, load_storyboard, log_call, retry, shot_by_id  # noqa: E402

STYLES = {
    "unhurried": None,  # the storyboard's current style_prompt
    "lively": ("Tell this like a lively, warm storyteller entertaining children: a natural brisk pace, "
               "expressive voices for the animals, no long pauses."),
}

if __name__ == "__main__":
    load_env()
    sys.stdout.reconfigure(encoding="utf-8")
    sb = load_storyboard()
    shot = shot_by_id(sb, sys.argv[1] if len(sys.argv) > 1 else "S10")
    text, voice, model = shot["narration"]["text"], sb["narration"]["voice"], narration.tts_model()
    d = OUT / "experiments"
    d.mkdir(parents=True, exist_ok=True)
    res = {}
    for label, style in STYLES.items():
        style = style or sb["narration"]["style_prompt"]
        t0 = time.time()
        audio, meta = retry(lambda: narration.synthesise(text, voice, style, model), stage="exp", tries=6)
        out = d / f"tts_pace_{shot['id']}_{label}.wav"
        secs = narration.write_wav(audio, out)
        log_call(stage="experiment", shot=shot["id"], provider="gemini", model=model, ok=True,
                 params={"experiment": "E3b tts pace", "label": label, "style": style, "voice": voice,
                         "chars": len(text)}, latency_s=time.time() - t0,
                 output=str(out.relative_to(OUT)), extra={"audio_s": round(secs, 2)})
        res[label] = secs
        print(f"{label:<10} {secs:5.2f}s  {len(text) / secs:.1f} chars/s  -> {out}")
    print(json.dumps(res))

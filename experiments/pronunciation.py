"""E8: fixing a TTS mispronunciation found in user test 1.

Viewer 2 heard S07's «ይካትዓኒ ኣሎ» ("he argues with me") as "ይካዓረኒሎ": the ት is dropped and the two words
merge. One variable per variant, same model (gemini-3.8-flash-tts), voice and base style as the film.

    python experiments/pronunciation.py          # writes outputs/experiments/pron_S07_<label>.wav

Listen, pick one, then apply it to storyboard.json and run `python film.py narration --only S07`.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import narration  # noqa: E402
from pipeline.common import OUT, load_env, load_storyboard, log_call, retry, shot_by_id  # noqa: E402

SHOT = "S07"
PREFIX = "ኣድጊ «ኦ ንጉስ፣ እዚ ሳዕሪ ሰማያዊ ምዃኑ "
VARIANTS = {
    # label: (text, extra style instruction)
    "A_style": (PREFIX + "ይካትዓኒ ኣሎ» በሎ።",
                " Pronounce every word fully and separately; say «ይካትዓኒ» and «ኣሎ» as two distinct words."),
    "B_eyu_zelo": (PREFIX + "ይካትዓኒ እዩ ዘሎ» በሎ።", ""),
    "C_synonym": (PREFIX + "ይከራኸረኒ ኣሎ» በሎ።", ""),
}

if __name__ == "__main__":
    load_env()
    sys.stdout.reconfigure(encoding="utf-8")
    sb = load_storyboard()
    voice, base, model = sb["narration"]["voice"], sb["narration"]["style_prompt"], narration.tts_model()
    print("current S07:", shot_by_id(sb, SHOT)["narration"]["text"])
    d = OUT / "experiments"
    d.mkdir(parents=True, exist_ok=True)
    for label, (text, extra) in VARIANTS.items():
        out = d / f"pron_{SHOT}_{label}.wav"
        if out.exists():
            print(f"{label}: exists, skipping")
            continue
        t0 = time.time()
        audio, _ = retry(lambda: narration.synthesise(text, voice, base + extra, model), stage="exp", tries=3)
        secs = narration.write_wav(audio, out)
        log_call(stage="experiment", shot=SHOT, provider="gemini", model=model, ok=True,
                 params={"experiment": "E8 pronunciation", "label": label, "text": text, "style_extra": extra},
                 latency_s=time.time() - t0, output=str(out.relative_to(OUT)), extra={"audio_s": round(secs, 2)})
        print(f"{label:<12} {secs:4.1f}s -> {out}")

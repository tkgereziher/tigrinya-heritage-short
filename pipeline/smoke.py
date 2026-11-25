"""Smoke test: call each hosted provider once, log latency to runs.jsonl, and probe the
narration language early. Also lists the Gemini models available to your key, because
model IDs change often.
"""
from __future__ import annotations

import os
import time

import requests

from . import keyframes, narration, script
from .common import OUT, load_env, log_call, need, say

STAGE = "smoke"
PROBES = {
    "ti": "ሰላም። እዚ ፈተና ድምጺ እዩ።",        # Tigrinya: "Hello. This is a voice test."
    "am": "ሰላም። ይህ የድምፅ ሙከራ ነው።",        # Amharic: same
    "en": "Hello. This is a voice test.",
}


def run() -> None:
    load_env()
    d = OUT / "smoke"
    d.mkdir(parents=True, exist_ok=True)
    key = need("GEMINI_API_KEY")

    t0 = time.time()
    r = requests.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                     headers={"x-goog-api-key": key}, timeout=60)
    names = [m["name"].split("/")[-1] for m in r.json().get("models", [])] if r.ok else []
    log_call(stage=STAGE, provider="gemini", model="models.list", params={}, latency_s=time.time() - t0,
             ok=r.ok, error=None if r.ok else r.text[:300])
    say(STAGE, f"gemini models: {len(names)}; TTS: {[n for n in names if 'tts' in n]}")
    say(STAGE, f"flash text models: {[n for n in names if 'flash' in n and 'tts' not in n][:12]}")

    results = {}
    try:
        txt = script.call("Reply with the JSON {\"ok\": true}", "smoke text")
        results["gemini text"] = f"ok {txt.strip()[:40]}"
    except Exception as e:  # noqa: BLE001
        results["gemini text"] = f"FAIL {str(e)[:120]}"

    model = narration.tts_model()
    for lang, text in PROBES.items():
        t0 = time.time()
        try:
            pcm, _ = narration.synthesise(text, "Kore", "Say calmly:", model)
            secs = narration.write_wav(pcm, d / f"tts_{lang}.wav")
            log_call(stage=STAGE, provider="gemini", model=model, params={"lang": lang, "probe": True},
                     latency_s=time.time() - t0, ok=True, extra={"audio_s": round(secs, 2)},
                     output=f"smoke/tts_{lang}.wav")
            results[f"tts {lang}"] = f"ok {secs:.1f}s audio in {time.time() - t0:.1f}s -> outputs/smoke/tts_{lang}.wav (LISTEN to it)"
        except Exception as e:  # noqa: BLE001
            log_call(stage=STAGE, provider="gemini", model=model, params={"lang": lang, "probe": True},
                     latency_s=time.time() - t0, ok=False, error=str(e)[:300])
            results[f"tts {lang}"] = f"FAIL {str(e)[:160]}"

    t0 = time.time()
    m = keyframes.image_model()
    try:
        raw = keyframes.generate("A clay coffee pot (jebena) on a woven mat, morning light, painterly.", 7, m)
        size = keyframes.save_png(raw, d / "image.png")
        log_call(stage=STAGE, provider="cloudflare", model=m, seed=7, params={"probe": True, "size": size},
                 latency_s=time.time() - t0, ok=True, output="smoke/image.png")
        results["cloudflare image"] = f"ok {size} in {time.time() - t0:.1f}s"
    except Exception as e:  # noqa: BLE001
        log_call(stage=STAGE, provider="cloudflare", model=m, params={"probe": True},
                 latency_s=time.time() - t0, ok=False, error=str(e)[:300])
        results["cloudflare image"] = f"FAIL {str(e)[:160]}"

    print("\nSMOKE TEST")
    for k, v in results.items():
        print(f"  {k:<18} {v}")
    print("\nModels in use (override in .env):",
          f"\n  GEMINI_TEXT_MODEL={script.text_model()}\n  GEMINI_TTS_MODEL={model}\n  CF_IMAGE_MODEL={m}")

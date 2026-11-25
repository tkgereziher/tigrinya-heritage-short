"""Stage: narration. One Gemini TTS call per shot -> outputs/narration/<shot>.wav

Line-by-line files make re-takes cheap: change one narration line in storyboard.json
and only that shot's audio is regenerated. Measured durations are written to
outputs/narration/timing.json, which the radio cut and the edit use to time shots.
"""
from __future__ import annotations

import base64
import json
import os
import time
import wave
from pathlib import Path

import requests

from .common import (D_NARR, Cache, Fatal, h, http_check, load_env, log_call, need,
                     retry, say, selected_shots)

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
STAGE = "narration"


def tts_model() -> str:
    # Gemini 3.8 Flash TTS lists Tigrinya; the Flash-Lite TTS model does not (checked 2026-11-25).
    return os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")


def _body(text: str, voice: str, style: str, legacy: bool) -> dict:
    if legacy:
        # Older TTS models: style goes in the prompt, voice via prebuiltVoiceConfig.
        prompt = f"{style.strip()}\n\n{text.strip()}" if style else text
        return {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["AUDIO"],
                                     "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    part = {"text": text.strip()}
    if style:
        part["speech_metadata"] = {"style": style.strip()}
    return {"contents": [{"role": "user", "parts": [part]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"voice": voice}}}}


def synthesise(text: str, voice: str, style: str, model: str) -> tuple[bytes, dict]:
    """Return audio bytes (a WAV file for 3.8 TTS, raw 24 kHz PCM for older models) and metadata."""
    key = need("GEMINI_API_KEY")
    legacy = os.environ.get("GEMINI_TTS_LEGACY") == "1" or "2.5" in model or "3.1" in model
    hdr = {"x-goog-api-key": key, "Content-Type": "application/json"}
    r = requests.post(API.format(model=model), json=_body(text, voice, style, legacy), timeout=180, headers=hdr)
    if r.status_code == 400 and not legacy:
        # Request shape changed between model generations; retry once with the legacy shape.
        r = requests.post(API.format(model=model), json=_body(text, voice, style, True), timeout=180, headers=hdr)
    http_check(r, STAGE)
    data = r.json()
    try:
        part = next(p["inlineData"] for p in data["candidates"][0]["content"]["parts"] if "inlineData" in p)
    except (KeyError, IndexError, StopIteration):
        raise Fatal(f"No audio in response: {json.dumps(data)[:400]}")
    return base64.b64decode(part["data"]), {"mime": part.get("mimeType"), "usage": data.get("usageMetadata")}


def write_wav(audio: bytes, path: Path, rate: int = 24000) -> float:
    """Write TTS audio as WAV (passes a complete WAV through; wraps raw PCM) and return seconds."""
    if audio[:4] == b"RIFF":
        path.write_bytes(audio)
    else:
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(audio)
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def run(sb: dict, only: list[str] | None = None, force: bool = False) -> dict:
    load_env()
    D_NARR.mkdir(parents=True, exist_ok=True)
    cache = Cache()
    model = tts_model()
    voice = sb["narration"]["voice"]
    style = sb["narration"]["style_prompt"]
    timing_path = D_NARR / "timing.json"
    timing = json.loads(timing_path.read_text(encoding="utf-8")) if timing_path.exists() else {}

    for shot in selected_shots(sb, only):
        sid, text = shot["id"], shot["narration"]["text"].strip()
        out = D_NARR / f"{sid}.wav"
        if not text:
            timing[sid] = 0.0
            say(STAGE, f"{sid} no narration")
            continue
        digest = h(model, voice, style, text, sb["language"]["code"])
        if not force and cache.fresh(f"{STAGE}/{sid}", digest, out):
            with wave.open(str(out), "rb") as w:
                timing[sid] = round(w.getnframes() / w.getframerate(), 3)
            say(STAGE, f"{sid} cached  {timing[sid]:.1f}s")
            timing_path.write_text(json.dumps(timing, indent=2), encoding="utf-8")
            continue

        t0 = time.time()
        try:
            # Free-tier TTS has a per-minute cap. We wait it out rather than switch models,
            # because a different TTS model is a different narrator voice mid-film.
            pcm, meta = retry(lambda: synthesise(text, voice, style, model), stage=STAGE, tries=6)
        except Exception as e:
            log_call(stage=STAGE, shot=sid, provider="gemini", model=model, ok=False,
                     params={"voice": voice, "lang": sb["language"]["code"], "chars": len(text)},
                     latency_s=time.time() - t0, error=str(e)[:500])
            raise
        dur = write_wav(pcm, out)
        lat = time.time() - t0
        timing[sid] = round(dur, 3)
        cache.put(f"{STAGE}/{sid}", digest)
        log_call(stage=STAGE, shot=sid, provider="gemini", model=model, ok=True,
                 params={"voice": voice, "lang": sb["language"]["code"], "chars": len(text),
                         "words": len(text.split()), "style": style},
                 latency_s=lat, output=str(out.relative_to(D_NARR.parent.parent)),
                 extra={"audio_s": round(dur, 3), "usage": meta.get("usage")})
        say(STAGE, f"{sid} regenerated  {dur:.1f}s audio in {lat:.1f}s")
        timing_path.write_text(json.dumps(timing, indent=2), encoding="utf-8")  # per shot: survives a crash

    timing_path.write_text(json.dumps(timing, indent=2), encoding="utf-8")
    total = sum(timing.get(s["id"], 0) for s in sb["shots"])
    say(STAGE, f"total narration {total:.1f}s")
    return timing

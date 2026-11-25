"""Stage: script. Gemini drafts a storyboard from story/brief.md, validated against the
schema; if validation fails, the errors are sent back once for a repair.

The draft is written to storyboard.draft.json - never straight over storyboard.json,
because the storyboard is a human-approved contract. Review it, then copy it across.
"""
from __future__ import annotations

import json
import os
import time

import requests

from .common import ROOT, SCHEMA, Fatal, Quota, http_check, load_env, log_call, need, retry, say

STAGE = "script"
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def text_model() -> str:
    return os.environ.get("GEMINI_TEXT_MODEL", "gemini-3.8-flash")


def strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    return t.strip()


def ask(prompt: str, model: str, json_out: bool = True, temperature: float = 0.7) -> tuple[str, dict]:
    # JSON is requested in the prompt and validated in code rather than via a provider-specific
    # JSON mode: the field name for that changed between API revisions (see FAILURES.md).
    key = need("GEMINI_API_KEY")
    r = requests.post(API.format(model=model), timeout=300,
                      headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                      json={"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": temperature}})
    http_check(r, STAGE, quota_fast=True)
    data = r.json()
    try:
        text ="".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError):
        raise Fatal(f"No text in response: {json.dumps(data)[:400]}")
    return (strip_fences(text) if json_out else text), data.get("usageMetadata", {})


def model_chain() -> list[str]:
    """Primary model, then fallbacks. Each Gemini model has its own per-minute/per-day limits,
    so rotating models on 429 (quota) or 503 (overload, FAILURES.md F5) keeps the stage moving."""
    fb = os.environ.get("GEMINI_TEXT_FALLBACKS", "gemini-3.6-flash,gemini-3.5-flash-lite,gemini-3.5-flash")
    return [text_model()] + [m.strip() for m in fb.split(",") if m.strip() and m.strip() != text_model()]


def call(prompt: str, purpose: str, json_out: bool = True) -> str:
    load_env()
    chain = model_chain()
    for i, model in enumerate(chain):
        t0 = time.time()
        try:
            text, usage = retry(lambda: ask(prompt, model, json_out), stage=STAGE, tries=3)
        except Exception as e:
            log_call(stage=STAGE, provider="gemini", model=model, ok=False, params={"purpose": purpose},
                     latency_s=time.time() - t0, error=str(e)[:500])
            if isinstance(e, Fatal) or i == len(chain) - 1:
                raise
            why = "quota hit" if isinstance(e, Quota) else "unavailable"
            say(STAGE, f"{model} {why}; switching to {chain[i + 1]}")
            continue
        log_call(stage=STAGE, provider="gemini", model=model, ok=True,
                 params={"purpose": purpose, "prompt_chars": len(prompt)}, latency_s=time.time() - t0,
                 extra={"usage": usage, "fallback_from": chain[0] if i else None})
        return text


def draft(brief_path=None) -> None:
    from .common import validate
    brief_path = brief_path or ROOT / "story" / "brief.md"
    brief = brief_path.read_text(encoding="utf-8")
    schema = SCHEMA.read_text(encoding="utf-8")
    prompt = f"""You are a documentary short-film writer and storyboard artist.
Write a storyboard for a 60-90 second vertical-first heritage short from the brief below.

Rules:
- 8 to 12 shots, about 6-8 seconds each. One idea and one gentle movement per shot.
- Vary shot sizes: open wide to establish place, medium for action, close-ups for feeling.
- Narration: short spoken sentences for the ear, roughly 130-200 words in total, in the
  narration language given in the brief, written in its native script. Give a faithful,
  natural English translation of each line in `english` (max ~80 characters per shot).
- image_prompt: subject, action, setting, composition, light. Do NOT repeat the style block
  or character descriptions; code appends those. No text or signs inside images.
- motion.prompt: ONLY motion and camera (e.g. "she slowly turns her head, camera pushes in gently").
- If the brief gives an original text, the narration must reuse its wording and dialogue, condensed.
  Do not invent new plot. Keep its key lines (the quarrel, the verdict, the lesson) word-for-word.
- Use the character ids, title, audience and intent given in the brief. Set title_native in native script.
- Every shot has a one-sentence `reason` stating why it exists.
- Fictional or stylised characters only unless the brief records consent.
- Give each shot a different integer seed. Score: instrumental, gentle texture, no lead melody
  under narration, a theme that returns at the end; bpm/key in their own fields.
- Output ONLY JSON that validates against this JSON Schema:

{schema}

BRIEF:
{brief}
"""
    out = ROOT / "storyboard.draft.json"
    text = call(prompt, "draft storyboard")
    for attempt in range(2):
        try:
            sb = json.loads(text)
            validate(sb)
            out.write_text(json.dumps(sb, indent=2, ensure_ascii=False), encoding="utf-8")
            say(STAGE, f"wrote {out.name} - review it, then copy to storyboard.json")
            return
        except (json.JSONDecodeError, SystemExit) as e:
            if attempt == 1:
                out.write_text(text, encoding="utf-8")
                raise SystemExit(f"Draft still invalid after repair; raw output in {out.name}:\n{e}")
            say(STAGE, "draft invalid, asking for a repair")
            text = call(f"This JSON failed validation:\n{e}\n\nReturn the corrected JSON only.\n\n{text}",
                        "repair storyboard")


def translate(lines: list[str], target: str) -> list[str]:
    """Translate a list of lines; used for extra-language experiments."""
    prompt = (f"Translate each line into {target}, natural spoken register, native script. "
              f"Return a JSON array of strings, same order and length.\n{json.dumps(lines, ensure_ascii=False)}")
    return json.loads(call(prompt, f"translate to {target}"))

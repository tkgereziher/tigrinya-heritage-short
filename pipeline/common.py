"""Shared plumbing for every stage: storyboard loading and validation, the run log,
content-hash caching, retries, and small FFmpeg helpers.

Every model call goes through `log_call`, which appends one JSON line to runs.jsonl.
Every cached artefact goes through `Cache`, which stores the hash of the inputs that
produced it in outputs/cache.json, so a re-run only regenerates what changed.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
STORYBOARD = ROOT / "storyboard.json"
SCHEMA = ROOT / "schema" / "storyboard.schema.json"
OUT = ROOT / "outputs"
RUNS = ROOT / "runs.jsonl"
CACHE_FILE = OUT / "cache.json"
ETHICS = ROOT / "ETHICS.md"

# Stage output folders
D_NARR = OUT / "narration"
D_KEY = OUT / "keyframes"
D_REF = OUT / "reference"
D_CLIPS = OUT / "clips"          # Wan 2.2 clips dropped here by the Kaggle notebook
D_SHOTS = OUT / "shots"          # rendered per-shot segments, per aspect ratio
D_MUSIC = OUT / "music"
D_FINAL = OUT / "final"
D_RADIO = OUT / "radio"

RATIOS = {"16x9": (1920, 1080), "9x16": (1080, 1920)}


# --------------------------------------------------------------------------- env

def load_env() -> None:
    """Load .env without adding a dependency. Real environment variables win."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def need(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Missing {name}. Copy .env.example to .env and fill it in.")
    return v


# ---------------------------------------------------------------------- logging

def say(stage: str, msg: str) -> None:
    print(f"[{stage:<10}] {msg}", flush=True)


def log_call(*, stage: str, model: str, provider: str, params: dict, latency_s: float,
             ok: bool, shot: str | None = None, seed: int | None = None,
             cost_usd: float = 0.0, list_price_usd: float | None = None,
             gpu_s: float | None = None, output: str | None = None,
             error: str | None = None, extra: dict | None = None) -> None:
    """Append one line per model call to runs.jsonl. Secrets never go in `params`."""
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stage": stage,
        "shot": shot,
        "provider": provider,
        "model": model,
        "seed": seed,
        "params": params,
        "latency_s": round(latency_s, 3),
        "gpu_s": gpu_s,
        "cost_usd": cost_usd,
        "list_price_usd": list_price_usd,
        "ok": ok,
        "output": output,
        "error": error,
    }
    if extra:
        rec.update(extra)
    with RUNS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------- storyboard

def load_storyboard(path: Path = STORYBOARD) -> dict:
    sb = json.loads(path.read_text(encoding="utf-8"))
    validate(sb)
    return sb


def validate(sb: dict) -> None:
    """Schema validation plus the checks a schema cannot express."""
    import jsonschema

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(sb), key=lambda e: list(e.path))
    problems = [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]

    ids = [s["id"] for s in sb.get("shots", [])]
    if len(ids) != len(set(ids)):
        problems.append("shots: duplicate shot ids")
    char_ids = {c["id"] for c in sb.get("characters", [])}
    for s in sb.get("shots", []):
        for c in s.get("characters", []):
            if c not in char_ids:
                problems.append(f"shots/{s['id']}: unknown character '{c}'")

    # Consent gate: a real person may not be generated without a record in ETHICS.md.
    ethics = ETHICS.read_text(encoding="utf-8") if ETHICS.exists() else ""
    for c in sb.get("characters", []):
        if c.get("real_person"):
            cid = c.get("consent_id", "")
            if not cid or f"consent_id: {cid}" not in ethics:
                problems.append(f"characters/{c['id']}: real_person without a matching "
                                f"'consent_id: {cid}' entry in ETHICS.md. Refusing to generate.")
    if problems:
        sys.exit("storyboard.json is invalid:\n  - " + "\n  - ".join(problems))


def shot_by_id(sb: dict, sid: str) -> dict:
    for s in sb["shots"]:
        if s["id"] == sid:
            return s
    raise KeyError(sid)


def selected_shots(sb: dict, only: list[str] | None) -> list[dict]:
    if not only:
        return sb["shots"]
    return [s for s in sb["shots"] if s["id"] in only]


# ------------------------------------------------------------------------ cache

def h(*parts: Any) -> str:
    """Stable short hash of JSON-serialisable parts and/or file paths (hashed by content)."""
    m = hashlib.sha256()
    for p in parts:
        if isinstance(p, Path):
            m.update(file_hash(p).encode() if p.exists() else b"<missing>")
        else:
            m.update(json.dumps(p, sort_keys=True, ensure_ascii=False).encode())
        m.update(b"|")
    return m.hexdigest()[:16]


def file_hash(p: Path) -> str:
    m = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            m.update(chunk)
    return m.hexdigest()[:16]


class Cache:
    """Maps '<stage>/<item>' -> input hash. An output is fresh if its file exists
    and the stored hash equals the hash of the current inputs."""

    def __init__(self) -> None:
        OUT.mkdir(parents=True, exist_ok=True)
        self.data = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}

    def fresh(self, key: str, digest: str, path: Path) -> bool:
        return path.exists() and self.data.get(key) == digest

    def put(self, key: str, digest: str) -> None:
        self.data[key] = digest
        CACHE_FILE.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------- retries

class Fatal(Exception):
    """An error that retrying will not fix (bad request, auth, unsupported language)."""


class Quota(Exception):
    """HTTP 429: this model's per-minute/per-day cap is hit. Retrying the same model wastes
    time; callers with a model chain switch to the next model instead."""


MAX_WAIT_S = 900  # waits longer than this are treated as "quota exhausted for the session"


def retry(fn: Callable[[], Any], *, tries: int = 4, base: float = 2.0, stage: str = "") -> Any:
    """Exponential backoff with jitter. Quota (429) and 5xx errors are retried;
    `Fatal` errors are raised immediately."""
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except (Fatal, Quota):
            raise
        except Exception as e:  # noqa: BLE001
            if attempt == tries:
                raise
            wait = base ** attempt + random.uniform(0, 1)
            # Honour an explicit retry hint from the provider if there is one.
            m = re.search(r"retry in ([0-9.]+)s", str(e), re.I)
            if m:
                wait = max(wait, float(m.group(1)) + 1)
                if wait > MAX_WAIT_S:
                    # A daily cap (FAILURES.md F9): fail fast instead of sleeping for a day.
                    raise Quota(f"provider asks to wait {wait / 3600:.1f} h (daily quota?). "
                                f"Switch model for this stage or rerun after the reset. {str(e)[:200]}")
            say(stage, f"attempt {attempt} failed ({str(e)[:160]}); retrying in {wait:.0f}s")
            time.sleep(wait)


def http_check(resp, stage: str, quota_fast: bool = False) -> None:
    """Raise Fatal for client errors that won't improve with a retry. With quota_fast,
    a 429 raises Quota so the caller can switch models instead of waiting."""
    hint = ""
    if resp.status_code == 429:
        # Google puts the wait in error.details[].retryDelay ("37s"); surface it for retry().
        m = re.search(r'"retryDelay"\s*:\s*"([0-9.]+)s"', resp.text)
        hint = f" (retry in {m.group(1)}s)" if m else " (retry in 60s)"
    if resp.status_code == 429 and quota_fast:
        raise Quota(f"HTTP 429{hint}: {resp.text[:300]}")
    if resp.status_code == 429 or resp.status_code >= 500:
        raise RuntimeError(f"HTTP {resp.status_code}{hint}: {resp.text[:300]}")
    if resp.status_code >= 400:
        raise Fatal(f"HTTP {resp.status_code}: {resp.text[:500]}")


# ----------------------------------------------------------------------- ffmpeg

def ffmpeg_bin(name: str = "ffmpeg") -> str:
    exe = shutil.which(name)
    if not exe and os.environ.get("LOCALAPPDATA"):
        # winget installs here; a terminal opened before the install won't have it on PATH yet.
        cand = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "WinGet" / "Links" / f"{name}.exe"
        exe = str(cand) if cand.exists() else None
    if not exe:
        sys.exit(f"{name} not found on PATH. Install it (Windows: winget install Gyan.FFmpeg) and reopen the terminal.")
    return exe


def run_ff(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", *args]
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + " ".join(cmd) + "\n" + p.stderr[-2000:])
    return p


def duration(path: Path) -> float:
    p = subprocess.run([ffmpeg_bin("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    return float(p.stdout.strip())


def loudness(path: Path) -> dict:
    """Measure integrated loudness / true peak with loudnorm's analysis pass."""
    cmd = [ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(path),
           "-af", "loudnorm=print_format=json", "-f", "null", "-"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr, re.S)
    return json.loads(m.group(0)) if m else {}


def normalise(src: Path, dst: Path, lufs: float, tp: float = -1.5) -> None:
    """Two-pass loudnorm to a target, keeping 48 kHz stereo."""
    m = loudness(src)
    if m and m.get("input_i") not in (None, "-inf"):
        f = (f"loudnorm=I={lufs}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
             f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    else:
        f = f"loudnorm=I={lufs}:TP={tp}:LRA=11"
    run_ff(["-i", str(src), "-af", f, "-ar", "48000", "-ac", "2", str(dst)])


def render_cfg(sb: dict) -> dict:
    r = sb.get("render", {})
    duck = {"threshold": 0.02, "ratio": 6, "attack_ms": 300, "release_ms": 1500, **r.get("duck", {})}
    return {
        "fps": r.get("fps", 24),
        "draft": r.get("draft", False),
        "voice_lufs": r.get("voice_lufs", -16.0),
        "music_lufs": sb["music"].get("music_lufs", -24.0),
        "target_lufs": r.get("target_lufs", -14.0),
        "true_peak_db": r.get("true_peak_db", -1.0),
        "duck": duck,
    }

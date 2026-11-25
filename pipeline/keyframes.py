"""Stage: keyframes. Cloudflare Workers AI (FLUX) -> outputs/keyframes/<shot>.png

Order matters: the reference sheet for each character is generated first
(outputs/reference/), the approved one is pinned by `reference_seed`, and every shot
is generated with the same fixed character description + style block. With a model
that accepts reference images (FLUX.2 klein), the approved reference image is also
sent as conditioning.
"""
from __future__ import annotations

import base64
import io
import os
import time
from pathlib import Path

import requests

from .common import (D_KEY, D_REF, Cache, Fatal, h, http_check, load_env, log_call,
                     need, retry, say, selected_shots)

STAGE = "keyframes"
API = "https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}"
COMPOSE = ("Subject centred in the frame with generous space on all sides, "
           "so the image can be cropped to both vertical and horizontal. No text, no letters, no watermark.")


def image_model() -> str:
    # klein-4B: Apache 2.0, multipart API, width/height, up to 4 reference images (<512px).
    # Fallback: @cf/black-forest-labs/flux-1-schnell (JSON API, no size control, no references).
    return os.environ.get("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-2-klein-4b")


def small_ref(p: Path) -> bytes:
    """Workers AI klein requires reference images smaller than 512x512."""
    from PIL import Image
    im = Image.open(p).convert("RGB")
    im.thumbnail((500, 500))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def is_klein(model: str) -> bool:
    return "flux-2" in model


def build_prompt(sb: dict, shot: dict) -> str:
    chars = {c["id"]: c for c in sb["characters"]}
    parts = [shot["image_prompt"].strip()]
    for cid in shot.get("characters", []):
        parts.append(f"{chars[cid].get('name', cid)}: {chars[cid]['description']}")
    parts += [sb["style"]["block"], COMPOSE]
    return " ".join(p.rstrip(".") + "." for p in parts)


def reference_prompt(sb: dict, char: dict) -> str:
    return (f"Character reference sheet of one person, full body front view and a head-and-shoulders portrait "
            f"side by side on a plain warm background. {char['description']}. {sb['style']['block']}. "
            f"No text, no letters.")


def generate(prompt: str, seed: int, model: str, width: int = 1024, height: int = 1024,
             refs: list[Path] | None = None, steps: int = 4) -> bytes:
    acct, token = need("CLOUDFLARE_ACCOUNT_ID"), need("CLOUDFLARE_API_TOKEN")
    url = API.format(acct=acct, model=model)
    headers = {"Authorization": f"Bearer {token}"}
    if is_klein(model):
        # FLUX.2 models on Workers AI take multipart form data; reference images go in as input_image_N.
        form = {"prompt": (None, prompt), "seed": (None, str(seed)), "width": (None, str(width)),
                "height": (None, str(height))}  # klein: steps fixed at 4
        files = {f"input_image_{i}": (p.name, small_ref(p), "image/png") for i, p in enumerate((refs or [])[:4])}
        r = requests.post(url, headers=headers, files={**form, **files}, timeout=180)
    else:
        r = requests.post(url, headers=headers, timeout=180,
                          json={"prompt": prompt, "steps": steps, "seed": seed})
    http_check(r, STAGE)
    if r.headers.get("content-type", "").startswith("image/"):
        return r.content
    data = r.json()
    if not data.get("success", True):
        raise Fatal(str(data.get("errors"))[:400])
    img = (data.get("result") or {}).get("image")
    if not img:
        raise Fatal(f"No image in response: {str(data)[:300]}")
    return base64.b64decode(img)


def save_png(raw: bytes, path: Path) -> tuple[int, int]:
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.save(path, "PNG")
    return im.size


NEURON_USD = 0.011 / 1000  # Workers AI paid rate beyond the 10,000 free neurons/day


def neurons(model: str, w: int, hgt: int, steps: int, n_refs: int = 0) -> float:
    """Neurons per image from the published Workers AI rates (checked 2026-11-25)."""
    tiles = max(1, -(-(w * hgt) // (512 * 512)))
    if "flux-2-klein" in model:
        return tiles * 26.05 + n_refs * 5.37
    return tiles * 4.80 + steps * 9.60  # flux-1-schnell


def list_price(model: str, w: int, hgt: int, steps: int, n_refs: int = 0) -> float:
    return round(neurons(model, w, hgt, steps, n_refs) * NEURON_USD, 6)


def _call(stage_key: str, prompt: str, seed: int, model: str, out: Path, shot: str | None,
          refs: list[Path] | None = None, w: int = 1024, hgt: int = 1024, steps: int = 4) -> None:
    t0 = time.time()
    try:
        raw = retry(lambda: generate(prompt, seed, model, w, hgt, refs, steps), stage=STAGE)
    except Exception as e:
        log_call(stage=STAGE, shot=shot, provider="cloudflare", model=model, seed=seed, ok=False,
                 params={"prompt": prompt, "w": w, "h": hgt, "steps": steps}, latency_s=time.time() - t0,
                 error=str(e)[:500])
        raise
    size = save_png(raw, out)
    log_call(stage=STAGE, shot=shot, provider="cloudflare", model=model, seed=seed, ok=True,
             params={"prompt": prompt, "w": size[0], "h": size[1], "steps": steps,
                     "refs": [str(p.name) for p in refs or []]},
             latency_s=time.time() - t0, list_price_usd=list_price(model, *size, steps, len(refs or [])),
             output=str(out.as_posix().split("outputs/", 1)[-1]),
             extra={"key": stage_key, "neurons": neurons(model, *size, steps, len(refs or []))})


def reference(sb: dict, variants: int = 4, force: bool = False) -> None:
    """Generate `variants` reference-sheet options per character. Pick one by setting
    characters[].reference_seed in storyboard.json."""
    load_env()
    D_REF.mkdir(parents=True, exist_ok=True)
    cache, model = Cache(), image_model()
    for c in sb["characters"]:
        prompt = reference_prompt(sb, c)
        seeds = [c["reference_seed"]] if c.get("reference_seed") is not None and variants <= 1 else \
            [1000 + i for i in range(variants)]
        for seed in seeds:
            out = D_REF / f"{c['id']}_{seed}.png"
            digest = h(model, prompt, seed)
            key = f"reference/{c['id']}_{seed}"
            if not force and cache.fresh(key, digest, out):
                say(STAGE, f"ref {c['id']} seed {seed} cached")
                continue
            _call(key, prompt, seed, model, out, shot=f"ref:{c['id']}", w=1024, hgt=1024)
            cache.put(key, digest)
            say(STAGE, f"ref {c['id']} seed {seed} regenerated")


def ref_images(sb: dict, shot: dict) -> list[Path]:
    out = []
    for c in sb["characters"]:
        if c["id"] in shot.get("characters", []) and c.get("reference_seed") is not None:
            p = D_REF / f"{c['id']}_{c['reference_seed']}.png"
            if p.exists():
                out.append(p)
    return out


def run(sb: dict, only: list[str] | None = None, force: bool = False, explore: int = 0) -> None:
    load_env()
    D_KEY.mkdir(parents=True, exist_ok=True)
    cache, model = Cache(), image_model()
    for shot in selected_shots(sb, only):
        sid = shot["id"]
        prompt = build_prompt(sb, shot)
        refs = ref_images(sb, shot) if is_klein(model) else []
        seed = shot.get("seed", 42)
        if explore:
            vdir = D_KEY / "variants"
            vdir.mkdir(exist_ok=True)
            for s in range(seed, seed + explore):
                out = vdir / f"{sid}_{s}.png"
                digest = h(model, prompt, s, *refs)
                if not force and cache.fresh(f"{STAGE}/variants/{sid}_{s}", digest, out):
                    continue
                _call(f"{STAGE}/variants/{sid}_{s}", prompt, s, model, out, sid, refs)
                cache.put(f"{STAGE}/variants/{sid}_{s}", digest)
                say(STAGE, f"{sid} variant seed {s} regenerated")
            continue
        out = D_KEY / f"{sid}.png"
        digest = h(model, prompt, seed, *refs)
        if not force and cache.fresh(f"{STAGE}/{sid}", digest, out):
            say(STAGE, f"{sid} cached")
            continue
        _call(f"{STAGE}/{sid}", prompt, seed, model, out, sid, refs)
        cache.put(f"{STAGE}/{sid}", digest)
        say(STAGE, f"{sid} regenerated")

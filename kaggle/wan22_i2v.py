"""Wan 2.2 TI2V-5B image-to-video, run on a Kaggle (2x T4) or Colab GPU.

Reads storyboard.json + outputs/keyframes/, writes for each shot:
  outputs/clips/<shot>.mp4    the clip
  outputs/clips/<shot>.json   sidecar: keyframe hash + motion prompt it was made from
  outputs/clips/runs_gpu.jsonl  one log line per generation (merge locally: python film.py ingest)

The local shots stage only uses a clip whose sidecar matches the *current* keyframe and
motion prompt, so a stale clip can never sneak into the film.

Kaggle cell (GPU T4 x2, Internet on):
    !git clone https://github.com/<you>/<repo>.git && cd <repo>
    !pip install -q "git+https://github.com/huggingface/diffusers" transformers accelerate ftfy imageio imageio-ffmpeg
    # one process per GPU, sharding the shots between them:
    !python kaggle/wan22_i2v.py --shard 0/2 --device cuda:0 & python kaggle/wan22_i2v.py --shard 1/2 --device cuda:1
    # then download outputs/clips/ (zip it) and unzip into your local outputs/clips/

Drafting at 832x480 with 81 frames and 30 steps keeps the weekly quota usable on a T4.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
NEG = ("blurry, distorted face, extra fingers, deformed hands, flicker, morphing, text, watermark, "
       "subtitles, oversaturated, static frame, low quality, jpeg artifacts")


def file_hash(p: Path) -> str:  # must match pipeline/common.py
    m = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            m.update(chunk)
    return m.hexdigest()[:16]


def load_pipe(device: str, dtype_name: str):
    import torch
    from diffusers import AutoencoderKLWan, WanImageToVideoPipeline
    dtype = {"fp16": torch.float16, "bf16": torch.bfloat16, "fp32": torch.float32}[dtype_name]
    vae = AutoencoderKLWan.from_pretrained(MODEL, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanImageToVideoPipeline.from_pretrained(MODEL, vae=vae, torch_dtype=dtype)
    pipe.enable_model_cpu_offload(gpu_id=int(device.split(":")[-1]) if ":" in device else 0)
    pipe.vae.enable_tiling()
    return pipe


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--storyboard", default=str(ROOT / "storyboard.json"))
    ap.add_argument("--keyframes", default=str(ROOT / "outputs" / "keyframes"))
    ap.add_argument("--out", default=str(ROOT / "outputs" / "clips"))
    ap.add_argument("--only", help="comma-separated shot ids")
    ap.add_argument("--shard", default="0/1", help="i/n: this process takes every n-th shot")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--width", type=int, default=832)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--frames", type=int, default=81, help="4k+1; 81 = 3.4 s at 24 fps")
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance", type=float, default=5.0)
    ap.add_argument("--dtype", default="fp16", choices=["fp16", "bf16", "fp32"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    import numpy as np
    import torch
    from diffusers.utils import export_to_video, load_image

    sb = json.loads(Path(a.storyboard).read_text(encoding="utf-8"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = out / "runs_gpu.jsonl"
    i, n = map(int, a.shard.split("/"))
    only = set(a.only.split(",")) if a.only else None
    todo = [s for s in sb["shots"] if s["motion"].get("use_video", True) and (not only or s["id"] in only)]
    todo = todo[i::n]
    gpu = torch.cuda.get_device_name(int(a.device.split(":")[-1])) if torch.cuda.is_available() else "cpu"
    print(f"{len(todo)} shot(s) on {gpu}: {[s['id'] for s in todo]}")

    pipe = None
    for s in todo:
        key = Path(a.keyframes) / f"{s['id']}.png"
        if not key.exists():
            print(f"{s['id']}: no keyframe, skipping")
            continue
        kh, prompt = file_hash(key), s["motion"]["prompt"]
        seed = s["motion"].get("seed", s.get("seed", 42))
        clip, side = out / f"{s['id']}.mp4", out / f"{s['id']}.json"
        if not a.force and clip.exists() and side.exists():
            m = json.loads(side.read_text(encoding="utf-8"))
            if m.get("keyframe_hash") == kh and m.get("motion_prompt") == prompt:
                print(f"{s['id']}: cached")
                continue
        if pipe is None:
            t_load = time.time()
            pipe = load_pipe(a.device, a.dtype)
            print(f"model loaded in {time.time() - t_load:.0f}s")
        params = {"w": a.width, "h": a.height, "frames": a.frames, "steps": a.steps,
                  "guidance": a.guidance, "dtype": a.dtype, "prompt": prompt}
        t0 = time.time()
        ok, err = True, None
        try:
            img = load_image(str(key)).resize((a.width, a.height))
            g = torch.Generator(device="cpu").manual_seed(seed)
            frames = pipe(image=img, prompt=prompt, negative_prompt=NEG, height=a.height, width=a.width,
                          num_frames=a.frames, num_inference_steps=a.steps, guidance_scale=a.guidance,
                          generator=g).frames[0]
            arr = np.asarray(frames)
            if not np.isfinite(arr).all() or arr.mean() < 0.01 * (255 if arr.max() > 1 else 1):
                raise RuntimeError("black/NaN frames - fp16 overflow? retry with --dtype bf16 or fp32")
            export_to_video(frames, str(clip), fps=24)
            side.write_text(json.dumps({"keyframe_hash": kh, "motion_prompt": prompt, "seed": seed,
                                        "model": MODEL, **params}, indent=2), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            ok, err = False, str(e)[:500]
            print(f"{s['id']}: FAILED {err}")
            torch.cuda.empty_cache()
        dt = time.time() - t0
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "stage": "shots", "shot": s["id"],
               "provider": "kaggle", "model": MODEL, "seed": seed, "params": params, "latency_s": round(dt, 1),
               "gpu_s": round(dt, 1), "gpu": "T4" if "T4" in gpu else gpu, "cost_usd": 0.0,
               "list_price_usd": None, "ok": ok, "output": f"clips/{clip.name}" if ok else None, "error": err}
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"{s['id']}: {'ok' if ok else 'fail'} in {dt:.0f}s")


if __name__ == "__main__":
    main()

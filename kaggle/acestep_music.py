"""ACE-Step 1.5 score candidates, run on a Kaggle / Colab GPU.

Reads the music cues from storyboard.json and writes, per cue and seed:
  outputs/music/candidates/<cue>_s<seed>.wav (+ .json sidecar with caption/bpm/key)
  outputs/music/candidates/runs_gpu.jsonl    (merge locally: python film.py ingest)

Choose one by setting music.chosen (and music.chosen_reason) in storyboard.json.

Kaggle cell (GPU, Internet on; ACE-Step needs Python 3.11-3.12):
    !git clone https://github.com/<you>/<repo>.git
    !git clone https://github.com/ACE-Step/ACE-Step-1.5.git && pip install -q -e ACE-Step-1.5
    !python <repo>/kaggle/acestep_music.py --acestep ACE-Step-1.5
    # download <repo>/outputs/music/candidates/ and unzip into your local outputs/music/candidates/

API per the ACE-Step 1.5 docs/en/INFERENCE.md (checked 2026-11-25). If the API has moved,
the Gradio UI (`acestep`) with the same caption/bpm/key/seed works; log the call by hand.
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--storyboard", default=str(ROOT / "storyboard.json"))
    ap.add_argument("--out", default=str(ROOT / "outputs" / "music" / "candidates"))
    ap.add_argument("--acestep", default="ACE-Step-1.5", help="path to the cloned ACE-Step-1.5 repo")
    ap.add_argument("--dit", default="acestep-v15-turbo")
    ap.add_argument("--lm", default="none",
                    help="planner LM, e.g. acestep-5Hz-lm-1.7B (what the auto-download fetches); default none")
    ap.add_argument("--seeds", default="", help="override cue seeds, e.g. 11,22,33")
    ap.add_argument("--offload", action="store_true", help="offload idle sub-models (VAE, text encoder) to CPU")
    ap.add_argument("--int8", action="store_true", help="int8 weight quantization (gave NaNs with fp16 on T4, F12)")
    ap.add_argument("--dtype", default="float32", choices=["float32", "float16", "bfloat16"],
                    help="float32 on pre-Ampere GPUs (T4): fp16 produced all-NaN latents (FAILURES.md F12)")
    a = ap.parse_args()

    # Kaggle's Jupyter exports MPLBACKEND=module://matplotlib_inline..., which a separate venv can't load,
    # and ACE-Step imports matplotlib indirectly (via lightning/torchmetrics). FAILURES.md F11.
    os.environ["MPLBACKEND"] = "Agg"
    # ACE-Step reads its compute dtype from this variable (its own NaN error message names it).
    os.environ["ACESTEP_DTYPE"] = a.dtype

    import torch
    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music

    sb = json.loads(Path(a.storyboard).read_text(encoding="utf-8"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = out / "runs_gpu.jsonl"
    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
    root = str(Path(a.acestep).resolve())

    t_load = time.time()
    dit = AceStepHandler()
    want = {"project_root": root, "config_path": a.dit, "device": "cuda"}
    if a.offload:
        want["offload_to_cpu"] = True
    if a.int8:
        want["quantization"] = "int8_weight_only"
    # Pass only the arguments this ACE-Step version accepts (the API was read from docs, not tested).
    accepted = inspect.signature(dit.initialize_service).parameters
    kw = want if any(p.kind == p.VAR_KEYWORD for p in accepted.values()) else {k: v for k, v in want.items() if k in accepted}
    dropped = sorted(set(want) - set(kw))
    if dropped:
        print(f"initialize_service does not accept {dropped}; continuing without them")
    print("initialize_service ->", dit.initialize_service(**kw))
    llm = None
    if a.lm != "none":
        try:
            from acestep.llm_inference import LLMHandler
            llm = LLMHandler()
            llm.initialize(checkpoint_dir=str(Path(root) / "checkpoints"), lm_model_path=a.lm, backend="pt", device="cuda")
        except Exception as e:  # noqa: BLE001
            # The planner LM is optional: the DiT alone still generates from the caption.
            print(f"LM planner unavailable ({str(e)[:200]}); generating without it")
            llm = None
    print(f"ACE-Step loaded on {gpu} in {time.time() - t_load:.0f}s")

    for cue in sb["music"]["cues"]:
        seeds = [int(x) for x in a.seeds.split(",")] if a.seeds else cue.get("seeds") or [11, 22, 33]
        lyrics = cue.get("lyrics", "[Instrumental]")
        p = GenerationParams(caption=cue["caption"], lyrics=lyrics, instrumental=lyrics.strip().lower() in
                             ("[instrumental]", "[inst]"), duration=cue["duration_s"],
                             bpm=cue.get("bpm"), keyscale=cue.get("key"))
        c = GenerationConfig(batch_size=len(seeds), use_random_seed=False, seeds=seeds, audio_format="wav")
        t0 = time.time()
        ok, err, paths = True, None, []
        try:
            tmp = out / "_tmp"
            res = generate_music(dit, llm, p, c, save_dir=str(tmp))
            audios = getattr(res, "audios", None) or []
            if not audios:
                # generate_music catches its own errors and returns an empty result; an empty result
                # must be logged as a failure, not "ok []" (my bug, first T4 run).
                why = next((str(getattr(res, k)) for k in ("error", "status_message", "message", "status")
                            if getattr(res, k, None)), "no audio returned (see ACE-Step log above)")
                raise RuntimeError(why[:400])
            for seed, audio in zip(seeds, audios):
                dst = out / f"{cue['id']}_s{seed}.wav"
                shutil.move(audio["path"], dst)
                dst.with_suffix(".json").write_text(json.dumps(
                    {"cue": cue["id"], "seed": seed, "caption": cue["caption"], "bpm": cue.get("bpm"),
                     "key": cue.get("key"), "duration_s": cue["duration_s"], "dit": a.dit, "lm": a.lm}, indent=2))
                paths.append(dst.name)
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception as e:  # noqa: BLE001
            ok, err = False, str(e)[:500]
            print(f"{cue['id']}: FAILED {err}")
        dt = time.time() - t0
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "stage": "music", "shot": None,
               "provider": "kaggle", "model": f"ACE-Step-1.5/{a.dit}+{a.lm}", "seed": seeds,
               "params": {"caption": cue["caption"], "bpm": cue.get("bpm"), "key": cue.get("key"),
                          "duration_s": cue["duration_s"], "batch": len(seeds), "offload": a.offload,
                          "int8": a.int8, "dtype": a.dtype},
               "latency_s": round(dt, 1), "gpu_s": round(dt, 1), "gpu": "T4" if "T4" in gpu else gpu,
               "cost_usd": 0.0, "list_price_usd": None, "ok": ok, "output": paths, "error": err}
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"{cue['id']}: {'ok' if ok else 'fail'} {paths} in {dt:.0f}s")


if __name__ == "__main__":
    main()

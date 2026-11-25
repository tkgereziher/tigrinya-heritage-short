"""Summarise runs.jsonl into the measured tables for COSTS.md.

Hosted calls carry latency and a list-price estimate; GPU calls (Kaggle) carry gpu_s.
Prints Markdown; `python film.py costs > outputs/costs_table.md` to save it.
"""
from __future__ import annotations

import json
from collections import defaultdict

from .common import RUNS

# List-price equivalents for free-tier GPU time (USD per GPU-hour), for comparison only.
GPU_HOUR_USD = {"T4": 0.35, "P100": 1.46, "A100": 3.67}


def run() -> None:
    if not RUNS.exists():
        print("runs.jsonl is empty - run something first")
        return
    rows = [json.loads(l) for l in RUNS.read_text(encoding="utf-8").splitlines() if l.strip()]
    agg = defaultdict(lambda: {"calls": 0, "ok": 0, "lat": [], "gpu": 0.0, "price": 0.0, "audio": 0.0})
    for r in rows:
        k = (r["stage"], r["provider"], r["model"])
        a = agg[k]
        a["calls"] += 1
        a["ok"] += bool(r.get("ok"))
        a["lat"].append(r.get("latency_s") or 0)
        a["gpu"] += r.get("gpu_s") or 0
        a["price"] += r.get("list_price_usd") or 0
        if r.get("gpu_s") and r.get("gpu"):
            a["price"] += (r["gpu_s"] / 3600) * GPU_HOUR_USD.get(r["gpu"], 0.35)
        a["audio"] += r.get("audio_s") or 0

    print("| stage | provider | model | calls | ok | median latency s | max latency s | GPU min | list-price USD |")
    print("|---|---|---|---|---|---|---|---|---|")
    tot_price = tot_gpu = 0.0
    for (stage, prov, model), a in sorted(agg.items()):
        lat = sorted(a["lat"])
        med = lat[len(lat) // 2] if lat else 0
        print(f"| {stage} | {prov} | {model} | {a['calls']} | {a['ok']} | {med:.1f} | {max(lat):.1f} | "
              f"{a['gpu'] / 60:.1f} | {a['price']:.4f} |")
        tot_price += a["price"]
        tot_gpu += a["gpu"]
    print(f"\n**Total:** {len(rows)} calls, {sum(a['ok'] for a in agg.values())} ok, "
          f"{tot_gpu / 60:.1f} GPU minutes, list-price equivalent ${tot_price:.2f}. Actual spend: $0.")
    fails = [r for r in rows if not r.get("ok")]
    if fails:
        print(f"\n**Failed calls:** {len(fails)}")
        for r in fails[-10:]:
            print(f"- {r['ts']} {r['stage']} {r.get('shot') or ''} {r['model']}: {(r.get('error') or '')[:120]}")

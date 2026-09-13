#!/usr/bin/env python3
"""Evaluate gateway moderation quality against a labeled dataset.

Usage:
  python scripts/evaluate.py --base-url http://localhost:8000/v1 \
    --api-key local-key --dataset evals/samples/sample_eval.jsonl \
    --model moderation-fast --out evals/reports/report.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx


def load_dataset(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        for line in text.splitlines():
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    else:
        data = json.loads(text)
        if isinstance(data, list):
            cases = data
        else:
            cases = data.get("cases", [])
    return cases


def score_case(pred_flagged: bool, gold_flagged: bool) -> str:
    if pred_flagged and gold_flagged:
        return "tp"
    if pred_flagged and not gold_flagged:
        return "fp"
    if not pred_flagged and gold_flagged:
        return "fn"
    return "tn"


def metrics(counts: dict[str, int]) -> dict[str, float]:
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    )
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positives": fp,
        "false_negatives": fn,
        "true_positives": tp,
        "true_negatives": counts["tn"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate moderation gateway")
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--api-key", default="change-me")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--model", default="moderation-fast")
    parser.add_argument("--out", default="evals/reports/latest_report.json")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    cases = load_dataset(Path(args.dataset))
    overall = defaultdict(int)
    by_lang: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    latencies: list[float] = []
    details: list[dict[str, Any]] = []

    headers = {
        "Authorization": f"Bearer {args.api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=args.timeout) as client:
        for case in cases:
            text = case["text"]
            gold = case.get("gold") or {}
            gold_flagged = bool(gold.get("flagged", False))
            lang = case.get("language", "unknown")
            started = time.perf_counter()
            try:
                resp = client.post(
                    f"{args.base_url.rstrip('/')}/moderations",
                    headers=headers,
                    json={"model": args.model, "input": text},
                )
                latency = (time.perf_counter() - started) * 1000.0
                latencies.append(latency)
                resp.raise_for_status()
                body = resp.json()
                pred = body["results"][0]["flagged"]
                bucket = score_case(pred, gold_flagged)
                overall[bucket] += 1
                by_lang[lang][bucket] += 1
                details.append(
                    {
                        "id": case.get("id"),
                        "language": lang,
                        "gold_flagged": gold_flagged,
                        "pred_flagged": pred,
                        "latency_ms": round(latency, 2),
                        "outcome": bucket,
                    }
                )
            except Exception as exc:
                overall["fn"] += 1
                by_lang[lang]["fn"] += 1
                details.append(
                    {
                        "id": case.get("id"),
                        "language": lang,
                        "error": str(exc)[:200],
                        "outcome": "error",
                    }
                )

    report = {
        "model": args.model,
        "dataset": str(args.dataset),
        "case_count": len(cases),
        "overall": metrics(overall),
        "by_language": {lang: metrics(c) for lang, c in by_lang.items()},
        "latency_ms": {
            "p50": round(statistics.median(latencies), 2) if latencies else None,
            "p95": (
                round(sorted(latencies)[int(0.95 * (len(latencies) - 1))], 2)
                if latencies
                else None
            ),
            "mean": round(statistics.mean(latencies), 2) if latencies else None,
        },
        "disclaimer": (
            "Scores are heuristic. This report does NOT claim equivalence to "
            "OpenAI omni-moderation-latest. Validate thresholds on your own data."
        ),
        "details": details,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("overall", "latency_ms", "case_count")}, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

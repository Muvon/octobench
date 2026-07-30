"""Assemble the combined full-bench table from paired provider results.

Usage:
  .venv/bin/python scripts/full_table.py 'results-full-claude/*/results.json' \
                                         'results-full-octomind/*/results.json'

Merges all matched results files per provider (dev + dev2 invocations), pairs
records by case_id, and prints a markdown table: validation, judge, final
score, cost, wall time per side, plus totals and per-language rollups.
"""
from __future__ import annotations

import glob
import json
import sys


def load(pattern: str) -> dict:
    records = {}
    for path in sorted(glob.glob(pattern)):
        data = json.loads(open(path).read())
        for r in data["results"]:
            records[r["case_id"]] = r
    return records


def fmt(r: dict | None) -> tuple:
    if r is None:
        return ("-", "-", "-", "-", "-")
    s = r.get("scoring", {})
    val = "FAIL" if s.get("validation_failed") else "PASS"
    if r.get("infra_failed"):
        val = "INFRA"
    judge = r.get("judge", {}).get("score")
    cost = r.get("cost_usd")
    mins = r.get("result", {}).get("elapsed_ms", 0) / 60000
    return (
        val,
        str(judge) if judge is not None else "?",
        f"{s.get('final_score', 0):.1f}",
        f"{cost:.2f}" if cost is not None else "?",
        f"{mins:.0f}m",
    )


def main() -> None:
    a = load(sys.argv[1])
    b = load(sys.argv[2])
    order = sorted(set(a) | set(b), key=lambda c: (c.split("_")[0], c.split("_")[1], c))

    print(f"| case | {'A:val':5} | A:j | A:final | A:$ | A:t "
          f"| {'B:val':5} | B:j | B:final | B:$ | B:t |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    tot = {"a": [0, 0, 0.0, 0.0, 0], "b": [0, 0, 0.0, 0.0, 0]}
    for cid in order:
        ra, rb = a.get(cid), b.get(cid)
        fa, fb = fmt(ra), fmt(rb)
        print(f"| {cid} | " + " | ".join(fa) + " | " + " | ".join(fb) + " |")
        for key, r in (("a", ra), ("b", rb)):
            if r is None:
                continue
            s = r.get("scoring", {})
            tot[key][0] += 0 if (s.get("validation_failed") or r.get("infra_failed")) else 1
            tot[key][1] += r.get("judge", {}).get("score") or 0
            tot[key][2] += s.get("final_score", 0)
            tot[key][3] += r.get("cost_usd") or 0
            tot[key][4] += r.get("result", {}).get("elapsed_ms", 0)
    n = len(order)
    for key, label in (("a", "A"), ("b", "B")):
        v, j, f, c, t = tot[key]
        print(f"\n{label}: pass {v}/{n} · judgeΣ {j} · finalΣ {f:.0f} · "
              f"${c:.2f} · {t/3600000:.1f}h")

    langs = sorted({c.split("_")[1] for c in order})
    print("\nPer-language pass (A/B):")
    for lang in langs:
        cases = [c for c in order if c.split("_")[1] == lang]
        pa = sum(1 for c in cases if a.get(c) and not (
            a[c]["scoring"].get("validation_failed") or a[c].get("infra_failed")))
        pb = sum(1 for c in cases if b.get(c) and not (
            b[c]["scoring"].get("validation_failed") or b[c].get("infra_failed")))
        print(f"  {lang}: {pa}/{len(cases)} vs {pb}/{len(cases)}")


if __name__ == "__main__":
    main()

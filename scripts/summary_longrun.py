#!/usr/bin/env python3
"""Print a comparison table from a long-run results.json.

Each result is a multi-turn sequence. Shows per-sequence aggregate metrics
and optional per-turn breakdown with --verbose.

Usage:
  python3 scripts/summary_longrun.py [path/to/results.json | results-dir]
  python3 scripts/summary_longrun.py --verbose
"""
from __future__ import annotations

import glob
import json
import os
import sys


def _latest_results(base: str = "results-longrun") -> str | None:
    hits = sorted(glob.glob(os.path.join(base, "*", "results.json")))
    return hits[-1] if hits else None


def _fmt(v, nd=4):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def main() -> None:
    verbose = "--verbose" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--verbose"]
    arg = args[0] if args else None

    if arg is None:
        path = _latest_results() or _latest_results("results-longrun-smoke")
    elif os.path.isdir(arg):
        path = _latest_results(arg)
    else:
        path = arg
    if not path or not os.path.exists(path):
        print(
            "No results.json found. Pass a path or run a long-run benchmark first.",
            file=sys.stderr,
        )
        sys.exit(1)

    data = json.load(open(path))
    rows = data.get("results", [])
    print(f"Results: {path}  ({len(rows)} sequence(s))\n")

    # Aggregate table.
    header = (
        f"{'sequence':36}{'provider':9}{'model':18}"
        f"{'turns':6}{'pass':6}{'rate':7}"
        f"{'sum':7}{'avg':6}{'cost$':9}{'tokens':>10}"
    )
    print(header)
    print("-" * len(header))

    for r in sorted(rows, key=lambda x: (x.get("sequence_id", ""), x.get("provider", ""))):
        agg = r.get("aggregate", {})
        line = (
            f"{r.get('sequence_id', '')[:35]:36}"
            f"{r.get('provider', '')[:8]:9}"
            f"{str(r.get('benchmark_model', ''))[:17]:18}"
            f"{agg.get('total_turns', 0):6}"
            f"{agg.get('passed', 0):6}"
            f"{_fmt(agg.get('pass_rate'), 2):7}"
            f"{_fmt(agg.get('sum_final_score'), 1):7}"
            f"{_fmt(agg.get('avg_final_score'), 1):6}"
            f"{_fmt(agg.get('total_cost_usd'), 4):9}"
            f"{_fmt(agg.get('total_tokens'), 0):>10}"
        )
        print(line)

    if not verbose:
        return

    # Per-turn breakdown.
    for r in sorted(rows, key=lambda x: (x.get("sequence_id", ""), x.get("provider", ""))):
        seq_id = r.get("sequence_id", "")
        provider = r.get("provider", "")
        print(f"\n{'':=<80}")
        print(f"{seq_id}  [{provider}]")
        print(f"{'':=<80}")
        th = f"  {'turn':5}{'name':40}{'valid':7}{'judge':6}{'final':7}{'cost$':9}{'tokens':>10}"
        print(th)
        print("  " + "-" * (len(th) - 2))
        for t in r.get("turns", []):
            sc = t.get("scoring", {})
            val = t.get("validation", {})
            tok = t.get("tokens", {})
            print(
                f"  {t.get('turn', 0):5}"
                f"{t.get('name', '')[:39]:40}"
                f"{('PASS' if val.get('passed') else 'FAIL'):7}"
                f"{_fmt(t.get('judge', {}).get('score'), 0):6}"
                f"{_fmt(sc.get('final_score'), 1):7}"
                f"{_fmt(t.get('cost_usd'), 4):9}"
                f"{_fmt(tok.get('total'), 0):>10}"
            )


if __name__ == "__main__":
    main()

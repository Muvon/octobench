#!/usr/bin/env python3
"""Print a comparison table from an octobench results.json.

Works for both the main runner (results/) and the SWE-bench runner
(results-swebench/). With no path, uses the newest results.json under results/.

Usage:
  python3 scripts/summary.py [path/to/results.json | results-dir]
"""
from __future__ import annotations

import glob
import json
import os
import sys


def _latest_results(base: str = "results") -> str | None:
    hits = sorted(glob.glob(os.path.join(base, "*", "results.json")))
    return hits[-1] if hits else None


def _fmt(v, nd=4):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg is None:
        path = _latest_results() or _latest_results("results-swebench")
    elif os.path.isdir(arg):
        path = _latest_results(arg)
    else:
        path = arg
    if not path or not os.path.exists(path):
        print("No results.json found. Pass a path or run a benchmark first.", file=sys.stderr)
        sys.exit(1)

    data = json.load(open(path))
    rows = data.get("results", [])
    print(f"Results: {path}  ({len(rows)} run(s))\n")

    has_sweb = any("swebench" in r for r in rows)
    header = (
        f"{'case':32}{'provider':9}{'model':18}{'exec':7}"
        f"{'verdict':9}{'elapsed':9}{'tokens':9}{'cost$':9}{'judge':6}{'final':7}"
    )
    if has_sweb:
        header += "resolved"
    print(header)
    print("-" * len(header))

    for r in sorted(rows, key=lambda x: (x.get("case_id", ""), x.get("provider", ""))):
        sc = r.get("scoring", {})
        j = r.get("judge", {})
        validate_ok = r.get("scripts", {}).get("validate", {}).get("exit_code", 1) == 0
        elapsed = r.get("result", {}).get("elapsed_ms", 0) / 1000.0
        line = (
            f"{r.get('case_id', '')[:31]:32}{r.get('provider', '')[:8]:9}"
            f"{str(r.get('model', ''))[:17]:18}{str(r.get('executor', 'host'))[:6]:7}"
            f"{('pass' if validate_ok else 'FAIL'):9}{elapsed:<9.1f}"
            f"{_fmt(r.get('tokens', {}).get('total')):9}{_fmt(r.get('cost_usd'), 4):9}"
            f"{_fmt(j.get('score'), 0):6}{_fmt(sc.get('final_score'), 1):7}"
        )
        if has_sweb:
            sw = r.get("swebench")
            line += (f"{sw.get('resolved')} (F2P {sw.get('fail_to_pass')})" if sw else "-")
        print(line)


if __name__ == "__main__":
    main()

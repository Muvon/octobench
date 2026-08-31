"""Recompute stored cost_usd from the current models.yaml price table.

Costs are computed at run time, so a price correction leaves every existing
record wrong. Token counts are the measurement; price is a lookup, so this
recomputes cost from the stored tokens rather than re-running anything.

Claude records are left alone: `provider_cost_usd` is what Anthropic actually
billed (including the 1h cache-write premium the flat table cannot express),
which beats a modelled number.

Usage:
  .venv/bin/python scripts/recost.py results-longrun-codex-luna/*/results.json
  .venv/bin/python scripts/recost.py --dry-run <paths...>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from scoring.aggregate import compute_cost

dry = "--dry-run" in sys.argv
paths = [p for p in sys.argv[1:] if not p.startswith("--")]
pricing_by_model = {
    name: spec.get("pricing") or {}
    for name, spec in (yaml.safe_load(Path("configs/models.yaml").read_text())["models"]).items()
}

for path in paths:
    data = json.loads(Path(path).read_text())
    changed = 0
    for seq in data.get("results", []):
        if seq.get("provider") == "claude":
            continue
        pricing = pricing_by_model.get(seq.get("benchmark_model"), {})
        if not pricing:
            print(f"  ! no pricing for {seq.get('benchmark_model')}, skipped")
            continue
        for turn in seq.get("turns") or []:
            tk = turn.get("tokens") or {}
            new = compute_cost(
                tk.get("input"),
                tk.get("cached_input"),
                tk.get("output"),
                pricing,
            )
            if new is None or abs(new - (turn.get("cost_usd") or 0)) < 1e-9:
                continue
            turn["cost_usd"] = new
            changed += 1
        turns = seq.get("turns") or []
        if turns and seq.get("aggregate"):
            seq["aggregate"]["total_cost_usd"] = round(
                sum(t["cost_usd"] or 0 for t in turns), 6
            )
    print(f"{path}: {changed} turn(s) recosted{' (dry run)' if dry else ''}")
    if not dry and changed:
        Path(path).write_text(json.dumps(data, indent=2))

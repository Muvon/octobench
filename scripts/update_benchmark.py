"""Regenerate the results block of BENCHMARK.md from current run data.

Usage:
  .venv/bin/python scripts/update_benchmark.py \
      'opus=results-full-claude/*/results.json' \
      'glm=results-full-octomind/*/results.json' \
      'codex=results-full-codex/*/results.json'

Splices the generated section between the RESULTS:BEGIN / RESULTS:END markers.
Providers whose glob matches nothing appear as pending columns; in-flight runs
simply show the cases recorded so far, so this is safe to run repeatedly.
"""
from __future__ import annotations

import datetime
import glob
import json
import re
import sys
from pathlib import Path

import yaml


def load(pattern: str) -> dict:
    records = {}
    for path in sorted(glob.glob(pattern)):
        try:
            data = json.loads(open(path).read())
        except Exception:
            continue
        for r in data.get("results", []):
            records[r["case_id"]] = r
    return records


def cell(r: dict | None) -> str:
    if r is None:
        return "-"
    if r.get("infra_failed"):
        return "INFRA"
    s = r.get("scoring", {})
    val = "FAIL" if s.get("validation_failed") else "PASS"
    judge = r.get("judge", {}).get("score")
    cost = r.get("cost_usd")
    mins = r.get("result", {}).get("elapsed_ms", 0) / 60000
    cost_s = f"${cost:.2f}" if cost is not None else "$?"
    return f"{val} j={judge if judge is not None else '?'} {cost_s} {mins:.0f}m"


def totals(records: dict, order: list) -> str:
    done = [records[c] for c in order if c in records]
    if not done:
        return "pending"
    ok = sum(1 for r in done if not (r["scoring"].get("validation_failed")
                                     or r.get("infra_failed")))
    j = sum(r.get("judge", {}).get("score") or 0 for r in done)
    cost = sum(r.get("cost_usd") or 0 for r in done)
    hours = sum(r.get("result", {}).get("elapsed_ms", 0) for r in done) / 3600000
    return f"**{ok}/{len(done)}** · judgeΣ {j} · ${cost:.2f} · {hours:.1f}h"


def discover_case_paths(repo_root: Path) -> dict[str, str]:
    """Map stable result IDs to the cases' current on-disk paths."""
    paths = {}
    cases_root = repo_root / "cases"
    for case_file in cases_root.rglob("case.yaml"):
        try:
            case = yaml.safe_load(case_file.read_text())
            case_id = case.get("id")
        except Exception:
            continue
        if case_id:
            paths[case_id] = case_file.parent.relative_to(cases_root).as_posix()
    return paths


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    case_paths = discover_case_paths(repo_root)
    providers = []
    for arg in sys.argv[1:]:
        label, pattern = arg.split("=", 1)
        providers.append((label, load(pattern)))

    order = sorted(
        {c for _, recs in providers for c in recs},
        key=lambda c: case_paths.get(c, c),
    )

    lines = []
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"_Updated {stamp}. val = hidden gold tests; j = judge 0-100; "
                 f"cost; wall time (incl. env setup + verification)._\n")
    header = "| case path | " + " | ".join(l for l, _ in providers) + " |"
    lines.append(header)
    lines.append("|---" * (len(providers) + 1) + "|")
    for cid in order:
        row = " | ".join(cell(recs.get(cid)) for _, recs in providers)
        lines.append(f"| {case_paths.get(cid, cid)} | {row} |")
    lines.append("")
    for label, recs in providers:
        lines.append(f"- **{label}**: {totals(recs, order)}")
    section = "\n".join(lines)

    bench = repo_root / "BENCHMARK.md"
    text = bench.read_text()
    new = re.sub(
        r"(<!-- RESULTS:BEGIN[^>]*-->\n).*?(<!-- RESULTS:END -->)",
        lambda m: m.group(1) + section + "\n" + m.group(2),
        text,
        flags=re.DOTALL,
    )
    bench.write_text(new)
    print(f"BENCHMARK.md results updated ({len(order)} cases, "
          f"{len(providers)} providers)")


if __name__ == "__main__":
    main()

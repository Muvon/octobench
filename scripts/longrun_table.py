"""Regenerate the long-run results block of BENCHMARK.md from sequence runs.

Usage:
  .venv/bin/python scripts/longrun_table.py \
      'opus=results-longrun-claude-mirror/results.corrected.json' \
      'gpt56-codex=results-longrun-codex-sol/*/results.json'

Same contract as update_benchmark.py: one column per label, later globs win,
a label whose glob matches nothing renders as a pending column, and a run in
flight simply shows the sequences recorded so far. Splices between the
LONGRUN-RESULTS:BEGIN / END markers.
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
    seqs: dict[str, dict] = {}
    for path in [p for g in pattern.split() for p in sorted(glob.glob(g))]:
        try:
            data = json.loads(open(path).read())
        except Exception:
            continue
        for r in data.get("results", []):
            # A setup-failed record has no turns and is not a result: letting it
            # win would erase the run it was meant to replace (a failed simdjson
            # rerun wiped opus's 5/5 exactly once).
            if not r.get("turns") and seqs.get(r["sequence_id"], {}).get("turns"):
                continue
            seqs[r["sequence_id"]] = r
    return seqs


def cell(seq: dict) -> str:
    agg = seq.get("aggregate") or {}
    turns = seq.get("turns") or []
    if not turns:
        return "setup-fail" if seq.get("error") else "—"
    minutes = round(sum(t["provider"]["elapsed_ms"] or 0 for t in turns) / 60000)
    return (
        f"{agg.get('passed', 0)}/{agg.get('total_turns', len(turns))} "
        f"Σ{agg.get('sum_final_score', 0):.1f} "
        f"${agg.get('total_cost_usd', 0):.2f} "
        f"{(agg.get('total_tokens') or 0) / 1e6:.1f}M {minutes}m"
    )


def main() -> None:
    suite = None
    marker = "LONGRUN-RESULTS"
    columns: list[tuple[str, dict]] = []
    for arg in sys.argv[1:]:
        if arg.startswith("--suite="):
            suite = arg.split("=", 1)[1]
            continue
        if arg.startswith("--markers="):
            marker = f"{arg.split('=', 1)[1]}-LONGRUN-RESULTS"
            continue
        label, _, pattern = arg.partition("=")
        columns.append((label, load(pattern)))
    if not columns:
        raise SystemExit(__doc__)

    # Rows come from the case tree, not from the results, so a campaign in
    # flight still shows every sequence it will eventually fill.
    # --suite scopes rows to the suite's longrun/ lines (mixed suites like gold
    # carry oneshot/ lines too; those belong to update_benchmark.py).
    rows = []
    for p in sorted(Path("cases/dev/longrun").rglob("sequence.yaml")):
        spec = yaml.safe_load(p.read_text())
        rows.append((f"{p.parent.parent.name}/{p.parent.name}", spec["id"], len(spec["turns"])))
    if suite:
        listing = Path("configs/suites") / f"{suite}.txt"
        if not listing.exists():
            raise SystemExit(f"no suite list at {listing}")
        wanted = {ln.strip().removeprefix("longrun/")
                  for ln in listing.read_text().splitlines()
                  if ln.strip().startswith("longrun/")}
        rows = [r for r in rows if r[0] in wanted]
        missing = wanted - {r[0] for r in rows}
        if missing:
            raise SystemExit(f"suite {suite} lists unknown sequences: {sorted(missing)}")

    lines = [
        f"_Updated {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC. "
        "Cell = passed/turns · Σ sum of turn final scores · cost · total tokens "
        "(incl. cache reads) · agent wall time (sum of agent invocations; "
        "excludes setup/validation/judging)._",
        "",
        "| sequence (turns) | " + " | ".join(c[0] for c in columns) + " |",
        "|---" * (len(columns) + 1) + "|",
    ]
    for path_label, sid, n_turns in rows:
        cells = [cell(c[1][sid]) if sid in c[1] else "—" for c in columns]
        lines.append(f"| {path_label} ({n_turns}) | " + " | ".join(cells) + " |")

    lines.append("")
    for label, seqs in columns:
        if not seqs:
            continue
        turns = [t for s in seqs.values() for t in (s.get("turns") or [])]
        passed = sum(1 for t in turns if t["validation"]["passed"])
        lines.append(
            f"- **{label}**: {len(seqs)}/{len(rows)} sequences · "
            f"{passed}/{len(turns)} turns passed · "
            f"ΣΣ {sum(t['scoring']['final_score'] for t in turns):.1f} · "
            f"${sum(t['cost_usd'] or 0 for t in turns):.2f} · "
            f"{sum(t['tokens']['total'] or 0 for t in turns) / 1e6:.0f}M tokens · "
            f"{sum(t['provider']['elapsed_ms'] or 0 for t in turns) / 3.6e6:.1f}h agent time"
        )

    bench = Path("BENCHMARK.md")
    text = bench.read_text()
    new = re.sub(
        rf"(<!-- {marker}:BEGIN[^>]*-->\n).*?(<!-- {marker}:END -->)",
        lambda m: m.group(1) + "\n".join(lines) + "\n" + m.group(2),
        text,
        flags=re.S,
    )
    if new == text:
        raise SystemExit(f"{marker} markers not found / block unchanged")
    bench.write_text(new)
    print(f"BENCHMARK.md updated ({len(columns)} columns, {len(rows)} sequences)")


if __name__ == "__main__":
    main()

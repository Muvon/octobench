"""Write the per-round GOLD record for one client/model column.

Usage:
  .venv/bin/python scripts/gold_rounds_report.py --suite=gold \
      --out=docs/gold/results/codex-gpt-6.1-sol.md \
      'codex gpt-6.1-sol=results-gold-gpt-6.1-sol-codex-r*/*/results.json'

BENCHMARK.md carries only the protocol aggregate from gold_scorecard.py. This
report keeps every round visible: a summary row per round, then one row per
item with one cell per round. Rounds and item loading reuse gold_scorecard, so
both reports read the same records (a later run directory inside a round
replaces an earlier result for the same item).
"""
from __future__ import annotations

import os
import statistics
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gold_scorecard import Item, _load_suite, _round_stats, load_column  # noqa: E402


def _count(value: Optional[float]) -> str:
    if value is None:
        return "UNKNOWN"
    if value >= 1_000_000:
        return f"{value / 1e6:.2f}M"
    if value >= 1_000:
        return f"{value / 1e3:.1f}K"
    return f"{value:.0f}"


def _minutes(elapsed_ms: float) -> str:
    return f"{elapsed_ms / 60000:.1f}m"


def _cost(items: List[Item]) -> str:
    known = [item.cost for item in items if item.cost is not None]
    if not known:
        return "UNKNOWN"
    suffix = "" if len(known) == len(items) else f" (+{len(items) - len(known)} unknown)"
    return f"${sum(known):.2f}{suffix}"


def _reasoning(items: List[Item]) -> Optional[int]:
    if any(item.reasoning is None for item in items):
        return None
    return sum(item.reasoning or 0 for item in items)


def _breakdown(items: List[Item]) -> List[str]:
    """fresh, cache read, output, reasoning, total, cost, agent time, efficiency score."""
    return [
        _count(sum(item.fresh_input for item in items)),
        _count(sum(item.cache_read for item in items)),
        _count(sum(item.output for item in items)),
        _count(_reasoning(items)),
        _count(sum(item.total_tokens for item in items)),
        _cost(items),
        _minutes(sum(item.elapsed_ms for item in items)),
        _efficiency(items),
    ]


BREAKDOWN_HEADER = (
    "Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score"
)


def _efficiency(items: List[Item]) -> str:
    scores = [item.efficiency_score for item in items if item.efficiency_score is not None]
    return f"{statistics.mean(scores):.1f}" if scores else "UNKNOWN"


def _round_key(round_id: str) -> int:
    return int(round_id[1:])


def _item_name(key: str) -> str:
    kind, _, rest = key.partition(":")
    return rest if kind == "oneshot" else rest.rsplit(":", 1)[0]


def _item_rows(rounds: Dict[str, Dict[str, Item]]) -> "OrderedDict[str, Dict[str, List[Item]]]":
    """Group items as one-shot case or long-run sequence, per round."""
    rows: "OrderedDict[str, Dict[str, List[Item]]]" = OrderedDict()
    keys = sorted(
        {key for items in rounds.values() for key in items},
        key=lambda key: (not key.startswith("oneshot:"), key),
    )
    for key in keys:
        rows.setdefault(_item_name(key), {})
    for round_id, items in rounds.items():
        for key, item in items.items():
            rows[_item_name(key)].setdefault(round_id, []).append(item)
    return rows


def _verdict(items: List[Item]) -> str:
    scored = [item for item in items if item.kind != "unscored"]
    if len(scored) == 1 and scored[0].kind == "oneshot":
        return "PASS" if scored[0].passed else "FAIL"
    return f"{sum(item.passed for item in scored)}/{len(scored)} turns"


def _turn_no(item: Item) -> int:
    return int(item.key.rsplit(":", 1)[1])


def _case_links(suite_name: Optional[str], out: Path) -> Dict[str, str]:
    """Map one-shot case ids and sequence ids to their manifests, relative to ``out``."""
    if not suite_name:
        return {}
    repo = Path(__file__).resolve().parent.parent
    suite = repo / "configs" / "suites" / f"{suite_name}.txt"
    links: Dict[str, str] = {}
    for raw in suite.read_text().splitlines():
        entry = raw.strip().split(":", 1)[0]
        if not entry or entry.startswith("#"):
            continue
        kind, lang, name = entry.split("/")
        manifest = repo / "cases" / "dev" / entry / ("case.yaml" if kind == "oneshot" else "sequence.yaml")
        target = os.path.relpath(manifest, out.resolve().parent)
        links[f"{kind}:{lang}:{name}"] = target
    return links


def _linked(name: str, links: Dict[str, str]) -> str:
    for key, target in links.items():
        kind, lang, entry = key.split(":")
        matched = (
            f"_{name}".endswith(f"_{entry}")
            if kind == "oneshot"
            else name.startswith(f"longrun_{lang}_{entry}")
        )
        if matched:
            return f"[`{name}`]({target})"
    return f"`{name}`"


def render(label: str, rounds: Dict[str, Dict[str, Item]], links: Optional[Dict[str, str]] = None) -> str:
    links = links or {}
    order = sorted(rounds, key=_round_key)
    rows = _item_rows(rounds)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    lines = [
        f"# GOLD rounds — {label}",
        "",
        f"_Generated {generated} by `scripts/gold_rounds_report.py`; do not hand-edit._",
        f"Rounds recorded: {len(order)}. The protocol aggregate is published in",
        "[BENCHMARK.md](../../../BENCHMARK.md) (GOLD section).",
        "",
        "Total tokens = fresh input + cache read + output (+ reasoning only where a client",
        "reports it separately; Codex output already includes reasoning). Agent time excludes",
        "setup, validation and judging. Unscored long-run turns are excluded from every sum.",
        "Eff. score is the mean harness efficiency score (0-100, compute_efficiency_score:",
        "exponential decay of agent time and cost); it is diagnostic and absolute.",
        "Missing evidence is UNKNOWN, never zero.",
        "",
        "## Per round",
        "",
        f"| Round | One-shots passed | Sequence turns passed | Unscored turns | {BREAKDOWN_HEADER} |",
        "|---" * 12 + "|",
    ]
    for round_id in order:
        items = list(rounds[round_id].values())
        stats = _round_stats(items)
        scored = [item for item in items if item.kind != "unscored"]
        lines.append(
            f"| {round_id} | {stats.oneshot_passed}/{stats.oneshot_total} "
            f"| {stats.longrun_turns_passed}/{stats.longrun_turns_total} "
            f"| {stats.longrun_turns_unscored} | " + " | ".join(_breakdown(scored)) + " |"
        )

    lines += [
        "",
        "## Across rounds",
        "",
        "Per item: rounds passed (sequences: scored turns passed over all rounds) and the",
        "median over rounds of total tokens, cost and agent time, and the mean efficiency score.",
        "",
        "| Item | Passed | Median total tokens | Median cost | Median agent time | Mean eff. score |",
        "|---|---|---|---|---|---|",
    ]
    for name, per_round in rows.items():
        samples = [
            [item for item in per_round[round_id] if item.kind != "unscored"]
            for round_id in order
            if round_id in per_round
        ]
        samples = [sample for sample in samples if sample]
        if not samples:
            continue
        if samples[0][0].kind == "oneshot":
            passed = f"{sum(sample[0].passed for sample in samples)}/{len(samples)} rounds"
        else:
            turns = [item for sample in samples for item in sample]
            passed = f"{sum(item.passed for item in turns)}/{len(turns)} turns"
        costs = [
            sum(item.cost for item in sample)
            for sample in samples
            if all(item.cost is not None for item in sample)
        ]
        lines.append(
            f"| {_linked(name, links)} | {passed} "
            f"| {_count(statistics.median(sum(i.total_tokens for i in s) for s in samples))} "
            f"| {'$%.2f' % statistics.median(costs) if costs else 'UNKNOWN'} "
            f"| {_minutes(statistics.median(sum(i.elapsed_ms for i in s) for s in samples))} "
            f"| {_efficiency([i for s in samples for i in s])} |"
        )

    for round_id in order:
        lines += [
            "",
            f"## Round {round_id} — per item",
            "",
            f"| Item | Verdict | {BREAKDOWN_HEADER} |",
            "|---" * 10 + "|",
        ]
        for name, per_round in rows.items():
            items = per_round.get(round_id)
            if not items:
                continue
            scored = [item for item in items if item.kind != "unscored"]
            lines.append(
                f"| {_linked(name, links)} | {_verdict(items)} | " + " | ".join(_breakdown(scored)) + " |"
            )
        for name, per_round in rows.items():
            items = per_round.get(round_id)
            if not items or items[0].kind == "oneshot":
                continue
            lines += [
                "",
                f"### Round {round_id} — `{name}` turns",
                "",
                f"| Turn | Status | {BREAKDOWN_HEADER} |",
                "|---" * 10 + "|",
            ]
            for item in sorted(items, key=_turn_no):
                if item.kind == "unscored":
                    lines.append(f"| {_turn_no(item)} | unscored (gold applied) |" + " — |" * 8)
                    continue
                status = "PASS" if item.passed else "FAIL"
                lines.append(
                    f"| {_turn_no(item)} | {status} | " + " | ".join(_breakdown([item])) + " |"
                )
    return "\n".join(lines) + "\n"


def main() -> None:
    suite_name: Optional[str] = None
    out: Optional[Path] = None
    columns: List[tuple] = []
    for argument in sys.argv[1:]:
        if argument.startswith("--suite="):
            suite_name = argument.split("=", 1)[1]
            continue
        if argument.startswith("--out="):
            out = Path(argument.split("=", 1)[1])
            continue
        label, separator, pattern = argument.partition("=")
        if not separator or not label or not pattern:
            raise SystemExit(f"invalid column argument: {argument}\n\n{__doc__}")
        columns.append((label, pattern))
    if len(columns) != 1 or out is None:
        raise SystemExit(__doc__)
    suite = _load_suite(suite_name) if suite_name else None
    label, pattern = columns[0]
    report = render(label, load_column(pattern, suite), _case_links(suite_name, out))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    print(report)


if __name__ == "__main__":
    main()

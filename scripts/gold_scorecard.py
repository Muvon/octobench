"""Generate the GOLD v2 solve-rate and efficiency report from stored results.

Usage:
  .venv/bin/python scripts/gold_scorecard.py [--suite=gold] [--markers=GOLD] \
      'claude=results-gold2-claude-r*/*/results.json' \
      'codex=results-gold2-codex-r*/*/results.json'

Each column keeps the existing ``label=<glob> [<glob>...]`` shape. Put every
one-shot and long-run result for a round under one ``--out`` directory, named
with an ``-rN`` or ``-roundN`` suffix, for example
``results-gold2-claude-r1``, ``-r2``, and ``-r3``. The top result directory is
the round boundary. Legacy directories without a round suffix are combined as
round 1, which keeps the published GOLD v1 result layout readable.

The report prints one Markdown table. ``--markers=GOLD`` also writes that table
between the GOLD-V2 markers in BENCHMARK.md, creating the block immediately
after the GOLD section introduction when it is absent.
"""
from __future__ import annotations

import glob
import json
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scoring.aggregate import normalize_token_counts  # noqa: E402


@dataclass(frozen=True)
class Suite:
    oneshot_suffixes: Set[str]
    longrun_turn_limits: Dict[str, Optional[int]]


@dataclass(frozen=True)
class Item:
    key: str
    kind: str
    sequence_id: Optional[str]
    passed: bool
    judge: Optional[float]
    cost: Optional[float]
    fresh_input: int
    cache_read: int
    output: int
    reasoning: int
    elapsed_ms: int


@dataclass(frozen=True)
class Totals:
    item_count: int
    known_cost: float
    unknown_costs: int
    fresh_input: int
    cache_read: int
    output: int
    reasoning: int
    elapsed_ms: int


@dataclass(frozen=True)
class RoundStats:
    oneshot_rate: Optional[float]
    oneshot_passed: int
    oneshot_total: int
    longrun_sequence_rate: Optional[float]
    longrun_sequences: int
    longrun_turns_passed: int
    longrun_turns_total: int
    judge_mean: Optional[float]
    totals: Totals


def _suite_path(name: str) -> Path:
    supplied = Path(name)
    if supplied.is_file():
        return supplied
    configured = REPO / "configs" / "suites" / f"{name}.txt"
    if not configured.is_file():
        raise SystemExit(f"no suite list at {configured}")
    return configured


def _load_suite(name: str) -> Suite:
    oneshot: Set[str] = set()
    longrun: Dict[str, Optional[int]] = {}
    for line_no, raw in enumerate(_suite_path(name).read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("oneshot/"):
            parts = line.split("/")
            if len(parts) != 3:
                raise SystemExit(f"invalid one-shot suite entry on line {line_no}: {line}")
            oneshot.add(f"_{parts[1]}_{parts[2]}")
            continue
        if line.startswith("longrun/"):
            path, separator, raw_limit = line.partition(":")
            parts = path.split("/")
            if len(parts) != 3:
                raise SystemExit(f"invalid long-run suite entry on line {line_no}: {line}")
            limit: Optional[int] = None
            if separator:
                try:
                    limit = int(raw_limit)
                except ValueError as exc:
                    raise SystemExit(
                        f"invalid long-run turn limit on line {line_no}: {line}"
                    ) from exc
                if limit < 1:
                    raise SystemExit(
                        f"long-run turn limit must be positive on line {line_no}: {line}"
                    )
            sequence_id = f"longrun_{parts[1]}_{parts[2]}"
            if sequence_id in longrun:
                raise SystemExit(f"duplicate long-run suite entry on line {line_no}: {line}")
            longrun[sequence_id] = limit
            continue
        raise SystemExit(f"invalid suite entry on line {line_no}: {line}")
    return Suite(oneshot, longrun)


def _result_dir(path: Path) -> Path:
    candidates = [parent for parent in path.parents if parent.name.startswith("results")]
    if not candidates:
        raise ValueError(f"result path is not under a results directory: {path}")
    return candidates[-1]


def _round_id(path: Path) -> str:
    result_dir = _result_dir(path)
    match = re.search(r"(?:^|[-_])(?:r|round)[-_]?(\d+)(?:$|[-_])", result_dir.name)
    return f"r{int(match.group(1))}" if match else "r1"


def _read_results(path: Path) -> List[dict]:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read result file {path}: {exc}") from exc
    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError(f"result file has no results list: {path}")
    return results


def _elapsed_ms(value: object, item_name: str) -> int:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{item_name} has no numeric agent elapsed_ms")
    return int(value)


def _tokens(block: object) -> Tuple[int, int, int, int]:
    if not isinstance(block, dict):
        raise ValueError("result item has no tokens block")
    return normalize_token_counts(block)


def _oneshot_item(record: dict, suite: Optional[Suite]) -> Optional[Item]:
    case_id = str(record["case_id"])
    if suite and not any(case_id.endswith(suffix) for suffix in suite.oneshot_suffixes):
        return None
    scoring = record.get("scoring") or {}
    validate = (record.get("scripts") or {}).get("validate") or {}
    passed = not scoring.get("validation_failed", validate.get("exit_code", 1) != 0)
    fresh, cache, output, reasoning = _tokens(record.get("tokens"))
    cost = record.get("cost_usd")
    return Item(
        key=f"oneshot:{case_id}",
        kind="oneshot",
        sequence_id=None,
        passed=passed,
        judge=(record.get("judge") or {}).get("score"),
        cost=float(cost) if cost is not None else None,
        fresh_input=fresh,
        cache_read=cache,
        output=output,
        reasoning=reasoning,
        elapsed_ms=_elapsed_ms((record.get("result") or {}).get("elapsed_ms"), case_id),
    )


def _longrun_items(record: dict, suite: Optional[Suite]) -> Iterable[Item]:
    sequence_id = str(record["sequence_id"])
    limit = None
    if suite:
        matches = [
            turn_limit
            for prefix, turn_limit in suite.longrun_turn_limits.items()
            if sequence_id.startswith(prefix)
        ]
        if not matches:
            return
        if len(matches) > 1:
            raise ValueError(f"sequence matches multiple suite entries: {sequence_id}")
        limit = matches[0]
    for turn in record.get("turns") or []:
        turn_no = int(turn["turn"])
        if limit is not None and turn_no > limit:
            continue
        fresh, cache, output, reasoning = _tokens(turn.get("tokens"))
        cost = turn.get("cost_usd")
        yield Item(
            key=f"longrun:{sequence_id}:{turn_no}",
            kind="longrun",
            sequence_id=sequence_id,
            passed=bool((turn.get("validation") or {}).get("passed")),
            judge=(turn.get("judge") or {}).get("score"),
            cost=float(cost) if cost is not None else None,
            fresh_input=fresh,
            cache_read=cache,
            output=output,
            reasoning=reasoning,
            elapsed_ms=_elapsed_ms(
                (turn.get("provider") or {}).get("elapsed_ms"),
                f"{sequence_id} turn {turn_no}",
            ),
        )


def load_column(pattern: str, suite: Optional[Suite]) -> Dict[str, Dict[str, Item]]:
    rounds: Dict[str, Dict[str, Item]] = {}
    paths = [Path(path) for part in pattern.split() for path in sorted(glob.glob(part))]
    for path in paths:
        items = rounds.setdefault(_round_id(path), {})
        for record in _read_results(path):
            if "case_id" in record:
                item = _oneshot_item(record, suite)
                if item is not None:
                    items[item.key] = item
            elif "sequence_id" in record:
                for item in _longrun_items(record, suite):
                    items[item.key] = item
    return rounds


def _totals(items: Iterable[Item]) -> Totals:
    materialized = list(items)
    known_costs = [item.cost for item in materialized if item.cost is not None]
    return Totals(
        item_count=len(materialized),
        known_cost=sum(known_costs),
        unknown_costs=len(materialized) - len(known_costs),
        fresh_input=sum(item.fresh_input for item in materialized),
        cache_read=sum(item.cache_read for item in materialized),
        output=sum(item.output for item in materialized),
        reasoning=sum(item.reasoning for item in materialized),
        elapsed_ms=sum(item.elapsed_ms for item in materialized),
    )


def _round_stats(items: Iterable[Item]) -> RoundStats:
    materialized = list(items)
    oneshot = [item for item in materialized if item.kind == "oneshot"]
    longrun = [item for item in materialized if item.kind == "longrun"]
    by_sequence: Dict[str, List[Item]] = {}
    for item in longrun:
        if item.sequence_id is None:
            raise ValueError(f"long-run item has no sequence: {item.key}")
        by_sequence.setdefault(item.sequence_id, []).append(item)
    sequence_rates = [
        sum(item.passed for item in turns) / len(turns) for turns in by_sequence.values()
    ]
    judges = [item.judge for item in materialized if item.judge is not None]
    return RoundStats(
        oneshot_rate=(sum(item.passed for item in oneshot) / len(oneshot) if oneshot else None),
        oneshot_passed=sum(item.passed for item in oneshot),
        oneshot_total=len(oneshot),
        longrun_sequence_rate=(statistics.mean(sequence_rates) if sequence_rates else None),
        longrun_sequences=len(sequence_rates),
        longrun_turns_passed=sum(item.passed for item in longrun),
        longrun_turns_total=len(longrun),
        judge_mean=statistics.mean(judges) if judges else None,
        totals=_totals(materialized),
    )


def _mean_range(values: Iterable[float], formatter) -> str:
    materialized = list(values)
    if not materialized:
        return "-"
    return (
        f"{formatter(statistics.mean(materialized))} "
        f"({formatter(min(materialized))}–{formatter(max(materialized))})"
    )


def _percent(value: float) -> str:
    return f"{100 * value:.1f}%"


def _number(value: float) -> str:
    return f"{value:.1f}"


def _tokens_count(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def _hours(value: float) -> str:
    return f"{value / 3_600_000:.1f}h"


def _cost_summary(totals: Iterable[Totals]) -> str:
    materialized = list(totals)
    if not materialized:
        return "-"
    known = [total.known_cost for total in materialized]
    unknown = sum(total.unknown_costs for total in materialized)
    prefix = "≥" if unknown else ""
    summary = _mean_range(known, lambda value: f"${value:.2f}")
    if unknown:
        noun = "item" if unknown == 1 else "items"
        summary = f"{prefix}{summary} · **UNKNOWN cost: {unknown} {noun}**"
    return summary


def _turn_summary(stats: Iterable[RoundStats]) -> str:
    materialized = [stat for stat in stats if stat.longrun_turns_total]
    if not materialized:
        return "-"
    mean_passed = statistics.mean(stat.longrun_turns_passed for stat in materialized)
    mean_total = statistics.mean(stat.longrun_turns_total for stat in materialized)
    ratios = sorted(
        (
            stat.longrun_turns_passed / stat.longrun_turns_total,
            stat.longrun_turns_passed,
            stat.longrun_turns_total,
        )
        for stat in materialized
    )
    low, high = ratios[0], ratios[-1]
    return (
        f"{mean_passed:.1f}/{mean_total:.1f} mean "
        f"({low[1]}/{low[2]}–{high[1]}/{high[2]})"
    )


def _oneshot_summary(stats: Iterable[RoundStats]) -> str:
    materialized = [stat for stat in stats if stat.oneshot_total]
    if not materialized:
        return "-"
    rates = _mean_range((stat.oneshot_rate for stat in materialized), _percent)
    passed = statistics.mean(stat.oneshot_passed for stat in materialized)
    total = statistics.mean(stat.oneshot_total for stat in materialized)
    return f"{rates} · {passed:.1f}/{total:.1f} mean"


def _longrun_summary(stats: Iterable[RoundStats]) -> str:
    materialized = [stat for stat in stats if stat.longrun_sequences]
    if not materialized:
        return "-"
    rates = _mean_range((stat.longrun_sequence_rate for stat in materialized), _percent)
    sequence_counts = [stat.longrun_sequences for stat in materialized]
    return (
        f"{rates} · {statistics.mean(sequence_counts):.1f} sequences mean "
        f"({min(sequence_counts)}–{max(sequence_counts)})"
    )


def _matched_keys(
    columns: List[Tuple[str, Dict[str, Dict[str, Item]]]]
) -> Dict[str, Set[str]]:
    if not columns or any(not rounds for _label, rounds in columns):
        return {}
    common_rounds = set.intersection(*(set(rounds) for _label, rounds in columns))
    matched: Dict[str, Set[str]] = {}
    for round_id in common_rounds:
        solved = [
            {key for key, item in rounds[round_id].items() if item.passed}
            for _label, rounds in columns
        ]
        matched[round_id] = set.intersection(*solved) if solved else set()
    return matched


def _metric_rows(
    columns: List[Tuple[str, Dict[str, Dict[str, Item]]]]
) -> List[Tuple[str, List[str]]]:
    matched = _matched_keys(columns)
    rows: List[Tuple[str, List[str]]] = []
    all_stats: Dict[str, List[RoundStats]] = {}
    matched_totals: Dict[str, List[Totals]] = {}
    for label, rounds in columns:
        all_stats[label] = [
            _round_stats(items.values()) for _round, items in sorted(rounds.items())
        ]
        matched_totals[label] = [
            _totals(rounds[round_id][key] for key in keys)
            for round_id, keys in sorted(matched.items())
            if round_id in rounds
        ]

    rows.append(("rounds", [str(len(rounds)) if rounds else "-" for _label, rounds in columns]))
    rows.append((
        "solve — one-shot pass rate",
        [_oneshot_summary(all_stats[label]) for label, _rounds in columns],
    ))
    rows.append((
        "solve — long-run mean sequence pass rate",
        [_longrun_summary(all_stats[label]) for label, _rounds in columns],
    ))
    rows.append((
        "solve — long-run turns passed/total",
        [_turn_summary(all_stats[label]) for label, _rounds in columns],
    ))
    rows.append((
        "diagnostic only — judge mean",
        [
            _mean_range(
                (stat.judge_mean for stat in all_stats[label] if stat.judge_mean is not None),
                _number,
            )
            for label, _rounds in columns
        ],
    ))

    total_fields = [
        ("cost", None, _cost_summary),
        ("fresh input tokens", "fresh_input", lambda values: _mean_range(values, _tokens_count)),
        ("cache read tokens", "cache_read", lambda values: _mean_range(values, _tokens_count)),
        ("output tokens", "output", lambda values: _mean_range(values, _tokens_count)),
        ("reasoning tokens", "reasoning", lambda values: _mean_range(values, _tokens_count)),
        ("agent time", "elapsed_ms", lambda values: _mean_range(values, _hours)),
    ]
    for scope, by_label in (
        (
            "all attempts",
            {label: [stat.totals for stat in all_stats[label]] for label, _ in columns},
        ),
        ("matched work", matched_totals),
    ):
        if scope == "matched work":
            rows.append((
                "efficiency — matched work items",
                [
                    _mean_range(
                        (total.item_count for total in by_label[label]),
                        lambda value: f"{value:.1f}",
                    )
                    for label, _rounds in columns
                ],
            ))
        for name, attribute, summarize in total_fields:
            cells = []
            for label, _rounds in columns:
                totals = by_label[label]
                if attribute is None:
                    cells.append(summarize(totals))
                else:
                    cells.append(summarize(getattr(total, attribute) for total in totals))
            rows.append((f"efficiency — {scope} — {name}", cells))
    return rows


def render(columns: List[Tuple[str, Dict[str, Dict[str, Item]]]]) -> str:
    if not any(rounds for _label, rounds in columns):
        raise SystemExit("no records matched")
    lines = [
        "| metric | " + " | ".join(label for label, _rounds in columns) + " |",
        "|---" * (len(columns) + 1) + "|",
    ]
    for metric, cells in _metric_rows(columns):
        lines.append(f"| {metric} | " + " | ".join(cells) + " |")
    lines.extend([
        "",
        "_Values are per-round means (min–max). Long-run solve rate gives every sequence "
        "equal weight; turn counts are shown separately. Matched work contains only one-shot "
        "cases and long-run turns solved by every reported column in the same round. Agent "
        "time excludes setup, validation, and judging. Judge mean is diagnostic only; GOLD "
        "does not combine solve and efficiency into a ranking score._",
    ])
    return "\n".join(lines)


def _write_marker_block(marker: str, report: str) -> None:
    marker_name = f"{marker}-V2"
    begin = (
        f"<!-- {marker_name}:BEGIN — regenerated by scripts/gold_scorecard.py "
        f"--markers={marker}; do not hand-edit -->"
    )
    end = f"<!-- {marker_name}:END -->"
    benchmark = REPO / "BENCHMARK.md"
    text = benchmark.read_text()
    escaped_marker = re.escape(marker_name)
    pattern = rf"<!-- {escaped_marker}:BEGIN[^>]*-->.*?<!-- {escaped_marker}:END -->"
    block = f"{begin}\n{report}\n{end}"
    if re.search(pattern, text, flags=re.S):
        updated = re.sub(pattern, block, text, count=1, flags=re.S)
    else:
        section = re.search(rf"^## {re.escape(marker)}\b.*$", text, flags=re.M)
        if section is None:
            raise SystemExit(f"section ## {marker} not found in BENCHMARK.md")
        next_marker = re.search(
            rf"^<!-- {re.escape(marker)}-", text[section.end() :], flags=re.M
        )
        if next_marker is None:
            raise SystemExit(f"no insertion point after ## {marker} introduction")
        insert_at = section.end() + next_marker.start()
        updated = text[:insert_at] + f"{block}\n\n" + text[insert_at:]
    benchmark.write_text(updated)


def main() -> None:
    suite_name: Optional[str] = None
    marker: Optional[str] = None
    raw_columns: List[Tuple[str, str]] = []
    for argument in sys.argv[1:]:
        if argument.startswith("--suite="):
            suite_name = argument.split("=", 1)[1]
            continue
        if argument.startswith("--markers="):
            marker = argument.split("=", 1)[1]
            continue
        label, separator, pattern = argument.partition("=")
        if not separator or not label or not pattern:
            raise SystemExit(f"invalid column argument: {argument}\n\n{__doc__}")
        raw_columns.append((label, pattern))
    if not raw_columns:
        raise SystemExit(__doc__)
    suite = _load_suite(suite_name) if suite_name else None
    columns = [(label, load_column(pattern, suite)) for label, pattern in raw_columns]
    report = render(columns)
    print(report)
    if marker:
        _write_marker_block(marker, report)


if __name__ == "__main__":
    main()

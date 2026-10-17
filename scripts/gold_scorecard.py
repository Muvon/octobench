"""Generate the GOLD solve-rate and efficiency report from stored results.

Usage:
  .venv/bin/python scripts/gold_scorecard.py [--suite=gold] [--markers=GOLD] \
      'claude=results-gold-claude-r*/*/results.json' \
      'codex=results-gold-codex-r*/*/results.json'

Each column keeps the existing ``label=<glob> [<glob>...]`` shape. Put every
one-shot and long-run result for a round under one ``--out`` directory, named
with an ``-rN`` or ``-roundN`` suffix, for example
``results-gold-claude-r1``, ``-r2``, and ``-r3``. The top result directory is
the round boundary. Legacy directories without a round suffix are combined as
round 1, which keeps the earlier published GOLD result layout readable.

The report prints one Markdown table. ``--markers=GOLD`` also writes that table
between the GOLD markers in BENCHMARK.md, creating the block immediately
after the GOLD section introduction when it is absent.
"""
from __future__ import annotations

import glob
import json
import math
import random
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scoring.aggregate import normalize_token_counts  # noqa: E402
from scoring.efficiency import (  # noqa: E402
    EfficiencyMetrics,
    extract_efficiency,
    geometric_mean,
    relative_index_ratios,
    relative_indexes,
)


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
    reasoning: Optional[int]
    elapsed_ms: int
    efficiency: Optional[EfficiencyMetrics]
    # Codex reports reasoning as a subset of output tokens; other clients report it separately.
    reasoning_in_output: bool = False
    assisted: bool = False

    @property
    def total_tokens(self) -> int:
        extra = 0 if self.reasoning_in_output or self.reasoning is None else self.reasoning
        return self.fresh_input + self.cache_read + self.output + extra


@dataclass(frozen=True)
class Totals:
    item_count: int
    known_cost: float
    unknown_costs: int
    fresh_input: int
    cache_read: int
    output: int
    reasoning: Optional[int]
    elapsed_ms: int
    total_tokens: int


@dataclass(frozen=True)
class RoundStats:
    oneshot_rate: Optional[float]
    oneshot_passed: int
    oneshot_total: int
    longrun_sequence_rate: Optional[float]
    longrun_sequences: int
    longrun_turns_passed: int
    longrun_turns_total: int
    longrun_turns_unscored: int
    assisted_turns_passed: int
    assisted_turns_total: int
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


def _oneshot_item(record: dict, suite: Optional[Suite], results_path: Path) -> Optional[Item]:
    case_id = str(record["case_id"])
    # Suffixes start with "_"; unprefixed ids ("js_gemini_...") equal the suffix minus it.
    if suite and not any(f"_{case_id}".endswith(suffix) for suffix in suite.oneshot_suffixes):
        return None
    scoring = record.get("scoring") or {}
    validate = (record.get("scripts") or {}).get("validate") or {}
    passed = not scoring.get("validation_failed", validate.get("exit_code", 1) != 0)
    fresh, cache, output, reasoning = _tokens(record.get("tokens"))
    record_dir = results_path.parent / case_id / str(record["setup"])
    reasoning_in_output = False
    if (record.get("tokens") or {}).get("reasoning") is None:
        reasoning = None
        if str(record["provider"]) == "codex":
            reasoning = _codex_reasoning_total(record_dir / "logs")
            reasoning_in_output = True
    cost = record.get("cost_usd")
    elapsed_ms = _elapsed_ms((record.get("result") or {}).get("elapsed_ms"), case_id)
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
        elapsed_ms=elapsed_ms,
        efficiency=extract_efficiency(
            str(record["provider"]),
            record_dir,
            elapsed_ms,
            status=(
                "killed_by_case_cap" if record.get("timed_out") is True else None
            ),
        ),
        reasoning_in_output=reasoning_in_output,
    )


def _codex_reasoning_total(log_dir: Path) -> Optional[int]:
    """Last cumulative ``reasoning_output_tokens`` codex reported for its thread."""
    raw = log_dir / "provider.raw.jsonl"
    if not raw.is_file():
        return None
    value: Optional[int] = None
    for line in raw.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "turn.completed":
            usage = event.get("usage")
            if isinstance(usage, dict) and isinstance(usage.get("reasoning_output_tokens"), int):
                value = usage["reasoning_output_tokens"]
    return value


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)


def _longrun_items(
    record: dict, suite: Optional[Suite], results_path: Path
) -> Iterable[Item]:
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
    # Codex usage counters are cumulative per thread; per-turn values are deltas.
    codex_reasoning_seen: Dict[str, int] = {}
    gold_restored = False
    for turn in record.get("turns") or []:
        turn_no = int(turn["turn"])
        if limit is not None and turn_no > limit:
            continue
        status = turn.get("status")
        if status == "unscored":
            gold_restored = True
            yield Item(
                key=f"unscored:{sequence_id}:{turn_no}",
                kind="unscored",
                sequence_id=sequence_id,
                passed=False,
                judge=None,
                cost=None,
                fresh_input=0,
                cache_read=0,
                output=0,
                reasoning=0,
                elapsed_ms=0,
                efficiency=None,
            )
            continue
        fresh, cache, output, reasoning = _tokens(turn.get("tokens"))
        reasoning_in_output = False
        cost = turn.get("cost_usd")
        provider_block = turn.get("provider") or {}
        elapsed_ms = _elapsed_ms(
            provider_block.get("elapsed_ms"),
            f"{sequence_id} turn {turn_no}",
        )
        run_name = (
            f"{record['provider']}__{_safe_id(str(record['benchmark_model']))}"
        )
        record_dir = (
            results_path.parent
            / sequence_id
            / run_name
            / "turns"
            / f"turn_{turn_no}"
        )
        if (turn.get("tokens") or {}).get("reasoning") is None:
            reasoning = None
            if str(record["provider"]) == "codex" and status != "not_run":
                reasoning_in_output = True
                cumulative = _codex_reasoning_total(record_dir / "logs")
                if cumulative is not None:
                    thread = str(provider_block.get("session_id") or "")
                    reasoning = max(cumulative - codex_reasoning_seen.get(thread, 0), 0)
                    codex_reasoning_seen[thread] = cumulative
        efficiency = None
        if status != "not_run":
            efficiency = extract_efficiency(
                str(record["provider"]),
                record_dir,
                elapsed_ms,
                provider_block.get("session_id"),
                1 if turn.get("session_mode") == "fresh" else None,
                str(status) if status is not None else None,
            )
        yield Item(
            key=f"longrun:{sequence_id}:{turn_no}",
            kind="longrun",
            sequence_id=sequence_id,
            passed=(
                False
                if status == "not_run"
                else bool((turn.get("validation") or {}).get("passed"))
            ),
            judge=(turn.get("judge") or {}).get("score"),
            cost=float(cost) if cost is not None else None,
            fresh_input=fresh,
            cache_read=cache,
            output=output,
            reasoning=reasoning,
            elapsed_ms=elapsed_ms,
            efficiency=efficiency,
            reasoning_in_output=reasoning_in_output,
            assisted=(
                status != "not_run"
                and (gold_restored or bool(turn.get("restored_dependencies")))
            ),
        )


def load_column(pattern: str, suite: Optional[Suite]) -> Dict[str, Dict[str, Item]]:
    rounds: Dict[str, Dict[str, Item]] = {}
    paths = [Path(path) for part in pattern.split() for path in sorted(glob.glob(part))]
    for path in paths:
        items = rounds.setdefault(_round_id(path), {})
        for record in _read_results(path):
            if "case_id" in record:
                item = _oneshot_item(record, suite, path)
                if item is not None:
                    items[item.key] = item
            elif "sequence_id" in record:
                for item in _longrun_items(record, suite, path):
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
        reasoning=(
            None
            if any(item.reasoning is None for item in materialized)
            else sum(item.reasoning or 0 for item in materialized)
        ),
        elapsed_ms=sum(item.elapsed_ms for item in materialized),
        total_tokens=sum(item.total_tokens for item in materialized),
    )


def _round_stats(items: Iterable[Item]) -> RoundStats:
    materialized = list(items)
    oneshot = [item for item in materialized if item.kind == "oneshot"]
    longrun = [item for item in materialized if item.kind == "longrun"]
    unscored = [item for item in materialized if item.kind == "unscored"]
    by_sequence: Dict[str, List[Item]] = {}
    for item in longrun:
        if item.sequence_id is None:
            raise ValueError(f"long-run item has no sequence: {item.key}")
        by_sequence.setdefault(item.sequence_id, []).append(item)
    sequence_rates = [
        sum(item.passed for item in turns) / len(turns) for turns in by_sequence.values()
    ]
    # Long-run judge prompts carried only changed file paths, not the diff, until
    # cli/longrun.py switched to build_evidence (2026-10-17); one-shots only.
    judges = [item.judge for item in oneshot if item.judge is not None]
    return RoundStats(
        oneshot_rate=(sum(item.passed for item in oneshot) / len(oneshot) if oneshot else None),
        oneshot_passed=sum(item.passed for item in oneshot),
        oneshot_total=len(oneshot),
        longrun_sequence_rate=(statistics.mean(sequence_rates) if sequence_rates else None),
        longrun_sequences=len(sequence_rates),
        longrun_turns_passed=sum(item.passed for item in longrun),
        longrun_turns_total=len(longrun),
        longrun_turns_unscored=len(unscored),
        assisted_turns_passed=sum(item.passed for item in longrun if item.assisted),
        assisted_turns_total=sum(item.assisted for item in longrun),
        judge_mean=statistics.mean(judges) if judges else None,
        totals=_totals(oneshot + longrun),
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


def _precise_hours(value: float) -> str:
    return f"{value / 3_600_000:.2f}h"


def _seconds(value: float) -> str:
    return f"{value / 1000:.1f}s"


def _dollars(value: float) -> str:
    return f"${value:.2f}"


def _dollars_per_hour(value: float) -> str:
    return f"${value:.2f}/h"


def _index(value: float) -> str:
    return f"{value:.2f}"


def _wilson_95(passed: int, total: int) -> Tuple[float, float]:
    if total <= 0:
        raise ValueError("Wilson interval requires a positive total")
    z = 1.959963984540054
    rate = passed / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(
        rate * (1 - rate) / total + z * z / (4 * total * total)
    ) / denominator
    return center - margin, center + margin


_BOOTSTRAP_SAMPLES = 10_000
_BOOTSTRAP_SEED = 20261017


def _percentile(values: List[float], probability: float) -> float:
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _bootstrap_geometric_ci(ratios: List[float]) -> Tuple[float, float]:
    if not ratios:
        raise ValueError("bootstrap interval requires at least one ratio")
    generator = random.Random(_BOOTSTRAP_SEED)
    estimates = sorted(
        math.exp(
            sum(math.log(ratios[generator.randrange(len(ratios))]) for _ in ratios)
            / len(ratios)
        )
        for _sample in range(_BOOTSTRAP_SAMPLES)
    )
    return _percentile(estimates, 0.025), _percentile(estimates, 0.975)


def _relative_index_ci(ratios: Optional[List[float]]) -> str:
    if ratios is None or not ratios:
        return "**UNKNOWN**"
    index = geometric_mean(ratios)
    if index is None:
        return "**UNKNOWN**"
    low, high = _bootstrap_geometric_ci(ratios)
    return f"{_index(index)} (95% CI {_index(low)}–{_index(high)})"


def _optional_summary(values: Iterable[Optional[float]], formatter) -> str:
    materialized = list(values)
    if not materialized:
        return "-"
    known = [value for value in materialized if value is not None]
    if not known:
        return "**UNKNOWN**"
    summary = _mean_range(known, formatter)
    unknown = len(materialized) - len(known)
    if unknown:
        noun = "round" if unknown == 1 else "rounds"
        summary += f" · **UNKNOWN: {unknown} {noun}**"
    return summary


def _known_cost(items: List[Item]) -> Optional[float]:
    if any(item.cost is None for item in items):
        return None
    return sum(item.cost for item in items if item.cost is not None)


def _cost_per_solve(items: List[Item]) -> Optional[float]:
    solved = sum(item.passed for item in items)
    cost = _known_cost(items)
    return cost / solved if cost is not None and solved else None


def _wall_time_per_solve(items: List[Item]) -> Optional[float]:
    solved = sum(item.passed for item in items)
    return sum(item.elapsed_ms for item in items) / solved if solved else None

def _tokens_per_solve(items: List[Item]) -> Optional[float]:
    solved = sum(item.passed for item in items)
    return sum(item.total_tokens for item in items) / solved if solved else None


def _burn_rate(items: List[Item]) -> Optional[float]:
    cost = _known_cost(items)
    wall_ms = sum(item.elapsed_ms for item in items)
    return cost * 3_600_000 / wall_ms if cost is not None and wall_ms else None


def _active_share(items: List[Item]) -> Optional[float]:
    measured = [item.efficiency for item in items if item.efficiency is not None]
    if not measured or any(efficiency.busy_ms is None for efficiency in measured):
        return None
    wall_ms = sum(efficiency.wall_ms for efficiency in measured)
    if not wall_ms:
        return None
    return sum(efficiency.busy_ms or 0 for efficiency in measured) / wall_ms


def _idle_ms(items: List[Item]) -> Optional[float]:
    measured = [item.efficiency for item in items if item.efficiency is not None]
    if not measured or any(efficiency.idle_ms is None for efficiency in measured):
        return None
    return float(sum(efficiency.idle_ms or 0 for efficiency in measured))


def _own_job_ms(items: List[Item]) -> Optional[float]:
    measured = [item.efficiency for item in items if item.efficiency is not None]
    if not measured or any(efficiency.own_job_ms is None for efficiency in measured):
        return None
    return float(sum(efficiency.own_job_ms or 0 for efficiency in measured))


def _stuck_wait_ms(items: List[Item]) -> Optional[float]:
    measured = [item.efficiency for item in items if item.efficiency is not None]
    if not measured or any(efficiency.stuck_wait_ms is None for efficiency in measured):
        return None
    return float(sum(efficiency.stuck_wait_ms or 0 for efficiency in measured))


_SILENT_GAP_THRESHOLD_MS = 5 * 60 * 1000


def _silent_gap_stats(items: List[Item]) -> Optional[Tuple[int, int]]:
    measured = [item.efficiency for item in items if item.efficiency is not None]
    if not measured or any(
        efficiency.longest_silent_gap_ms is None for efficiency in measured
    ):
        return None
    gaps = [
        efficiency.longest_silent_gap_ms
        for efficiency in measured
        if efficiency.longest_silent_gap_ms is not None
    ]
    return max(gaps), sum(gap >= _SILENT_GAP_THRESHOLD_MS for gap in gaps)


def _silent_gap_summary(rounds: Iterable[List[Item]]) -> str:
    materialized = list(rounds)
    if not materialized:
        return "-"
    stats = [_silent_gap_stats(items) for items in materialized]
    known = [stat for stat in stats if stat is not None]
    if not known:
        return "**UNKNOWN**"
    gap_summary = _mean_range((stat[0] for stat in known), _seconds)
    count_summary = _mean_range((stat[1] for stat in known), lambda value: f"{value:.1f}")
    summary = f"{gap_summary} · ≥5m: {count_summary} records"
    unknown = len(stats) - len(known)
    if unknown:
        noun = "round" if unknown == 1 else "rounds"
        summary += f" · **UNKNOWN: {unknown} {noun}**"
    return summary


def _headline_index(
    cost_index: Optional[float], time_index: Optional[float]
) -> Optional[float]:
    if cost_index is None or time_index is None:
        return None
    return geometric_mean([cost_index, time_index])


def _waste_share(items: List[Item]) -> Optional[float]:
    measured = [item.efficiency for item in items if item.efficiency is not None]
    if not measured:
        return None
    if any(
        efficiency.tool_calls is None
        or efficiency.repeat_calls is None
        or efficiency.filler_calls is None
        for efficiency in measured
    ):
        return None
    calls = sum(efficiency.tool_calls or 0 for efficiency in measured)
    if not calls:
        return None
    waste = sum(
        (efficiency.repeat_calls or 0) + (efficiency.filler_calls or 0)
        for efficiency in measured
    )
    return waste / calls


def _mean_tail_ms(items: List[Item]) -> Optional[float]:
    measured = [item.efficiency for item in items if item.efficiency is not None]
    if not measured or any(efficiency.tail_ms is None for efficiency in measured):
        return None
    return statistics.mean(
        efficiency.tail_ms
        for efficiency in measured
        if efficiency.tail_ms is not None
    )


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
    passed = sum(stat.longrun_turns_passed for stat in materialized)
    total = sum(stat.longrun_turns_total for stat in materialized)
    low, high = _wilson_95(passed, total)
    return (
        f"{_percent(passed / total)} (95% CI {_percent(low)}–{_percent(high)}) "
        f"· {passed}/{total} pooled"
    )


def _assisted_summary(stats: Iterable[RoundStats]) -> str:
    materialized = list(stats)
    passed = sum(stat.assisted_turns_passed for stat in materialized)
    total = sum(stat.assisted_turns_total for stat in materialized)
    return f"{passed}/{total} pooled" if total else "-"


def _unscored_summary(stats: Iterable[RoundStats]) -> str:
    materialized = [
        stat
        for stat in stats
        if stat.longrun_turns_total or stat.longrun_turns_unscored
    ]
    if not materialized:
        return "-"
    return _mean_range(
        (stat.longrun_turns_unscored for stat in materialized),
        lambda value: f"{value:.1f}",
    )


def _oneshot_summary(stats: Iterable[RoundStats]) -> str:
    materialized = [stat for stat in stats if stat.oneshot_total]
    if not materialized:
        return "-"
    passed = sum(stat.oneshot_passed for stat in materialized)
    total = sum(stat.oneshot_total for stat in materialized)
    low, high = _wilson_95(passed, total)
    return (
        f"{_percent(passed / total)} (95% CI {_percent(low)}–{_percent(high)}) "
        f"· {passed}/{total} pooled"
    )


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
    all_items: Dict[str, List[List[Item]]] = {}
    matched_totals: Dict[str, List[Totals]] = {}
    for label, rounds in columns:
        all_items[label] = [
            [item for item in items.values() if item.kind != "unscored"]
            for _round, items in sorted(rounds.items())
        ]
        all_stats[label] = [
            _round_stats(items.values()) for _round, items in sorted(rounds.items())
        ]
        matched_totals[label] = [
            _totals(rounds[round_id][key] for key in keys)
            for round_id, keys in sorted(matched.items())
            if round_id in rounds
        ]

    relative_cost: Dict[str, List[Optional[float]]] = {
        label: [] for label, _rounds in columns
    }
    relative_time: Dict[str, List[Optional[float]]] = {
        label: [] for label, _rounds in columns
    }
    relative_cost_excluded: Dict[str, List[int]] = {
        label: [] for label, _rounds in columns
    }
    relative_time_excluded: Dict[str, List[int]] = {
        label: [] for label, _rounds in columns
    }
    relative_tokens: Dict[str, List[Optional[float]]] = {
        label: [] for label, _rounds in columns
    }
    relative_tokens_excluded: Dict[str, List[int]] = {
        label: [] for label, _rounds in columns
    }
    for round_id, keys in sorted(matched.items()):
        cost_indexes, cost_excluded = relative_indexes(
            {
                label: {key: rounds[round_id][key].cost for key in keys}
                for label, rounds in columns
            }
        )
        time_indexes, time_excluded = relative_indexes(
            {
                label: {
                    key: float(rounds[round_id][key].elapsed_ms) for key in keys
                }
                for label, rounds in columns
            }
        )
        token_indexes, token_excluded = relative_indexes(
            {
                label: {
                    key: float(rounds[round_id][key].total_tokens) for key in keys
                }
                for label, rounds in columns
            }
        )
        for label, _rounds in columns:
            relative_cost[label].append(cost_indexes[label])
            relative_time[label].append(time_indexes[label])
            relative_cost_excluded[label].append(cost_excluded)
            relative_time_excluded[label].append(time_excluded)
            relative_tokens[label].append(token_indexes[label])
            relative_tokens_excluded[label].append(token_excluded)

    pooled_cost_ratios, _cost_excluded = relative_index_ratios(
        {
            label: {
                f"{round_id}:{key}": rounds[round_id][key].cost
                for round_id, keys in sorted(matched.items())
                for key in keys
            }
            for label, rounds in columns
        }
    )
    pooled_time_ratios, _time_excluded = relative_index_ratios(
        {
            label: {
                f"{round_id}:{key}": float(rounds[round_id][key].elapsed_ms)
                for round_id, keys in sorted(matched.items())
                for key in keys
            }
            for label, rounds in columns
        }
    )
    pooled_token_ratios, _token_excluded = relative_index_ratios(
        {
            label: {
                f"{round_id}:{key}": float(rounds[round_id][key].total_tokens)
                for round_id, keys in sorted(matched.items())
                for key in keys
            }
            for label, rounds in columns
        }
    )

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
        "solve — assisted long-run turns passed/total",
        [_assisted_summary(all_stats[label]) for label, _rounds in columns],
    ))
    rows.append((
        "not scored — long-run turns",
        [_unscored_summary(all_stats[label]) for label, _rounds in columns],
    ))
    rows.append((
        "diagnostic only — judge mean (one-shots)",
        [
            _mean_range(
                (stat.judge_mean for stat in all_stats[label] if stat.judge_mean is not None),
                _number,
            )
            for label, _rounds in columns
        ],
    ))
    rows.append((
        "efficiency-only headline — matched work cost/time index",
        [
            _optional_summary(
                (
                    _headline_index(cost_index, time_index)
                    for cost_index, time_index in zip(
                        relative_cost[label], relative_time[label]
                    )
                ),
                _index,
            )
            for label, _rounds in columns
        ],
    ))
    all_attempt_metrics = [
        ("cost per solve", _cost_per_solve, _dollars),
        ("wall time per solve", _wall_time_per_solve, _precise_hours),
        ("tokens per solve", _tokens_per_solve, _tokens_count),
        ("burn rate", _burn_rate, _dollars_per_hour),
        ("active share", _active_share, _percent),
        ("idle time", _idle_ms, _hours),
        ("own-job wait", _own_job_ms, _precise_hours),
        ("stuck wait", _stuck_wait_ms, _precise_hours),
        ("waste share", _waste_share, _percent),
        ("mean tail after final answer", _mean_tail_ms, _seconds),
    ]
    for name, calculate, formatter in all_attempt_metrics:
        rows.append((
            f"efficiency — all attempts — {name}",
            [
                _optional_summary(
                    (calculate(items) for items in all_items[label]), formatter
                )
                for label, _rounds in columns
            ],
        ))
    rows.append((
        "efficiency — all attempts — longest silent gap",
        [
            _silent_gap_summary(all_items[label])
            for label, _rounds in columns
        ],
    ))

    total_fields = [
        ("cost", None, _cost_summary),
        ("fresh input tokens", "fresh_input", lambda values: _mean_range(values, _tokens_count)),
        ("cache read tokens", "cache_read", lambda values: _mean_range(values, _tokens_count)),
        ("output tokens", "output", lambda values: _mean_range(values, _tokens_count)),
        (
            "reasoning tokens (codex: subset of output)",
            "reasoning",
            lambda values: _optional_summary(values, _tokens_count),
        ),
        ("total tokens", "total_tokens", lambda values: _mean_range(values, _tokens_count)),
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

    rows.append((
        "efficiency — matched work — relative cost index",
        [
            _relative_index_ci(pooled_cost_ratios[label])
            for label, _rounds in columns
        ],
    ))
    rows.append((
        "efficiency — matched work — zero-cost items excluded from relative index",
        [
            _mean_range(relative_cost_excluded[label], lambda value: f"{value:.0f}")
            for label, _rounds in columns
        ],
    ))
    rows.append((
        "efficiency — matched work — relative time index",
        [
            _relative_index_ci(pooled_time_ratios[label])
            for label, _rounds in columns
        ],
    ))
    rows.append((
        "efficiency — matched work — zero-time items excluded from relative index",
        [
            _mean_range(relative_time_excluded[label], lambda value: f"{value:.0f}")
            for label, _rounds in columns
        ],
    ))
    rows.append((
        "efficiency — matched work — relative token index",
        [
            _relative_index_ci(pooled_token_ratios[label])
            for label, _rounds in columns
        ],
    ))
    rows.append((
        "efficiency — matched work — zero-token items excluded from relative index",
        [
            _mean_range(relative_tokens_excluded[label], lambda value: f"{value:.0f}")
            for label, _rounds in columns
        ],
    ))
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
        "_Most totals and all-attempt metrics are per-round means (min–max); pooled rates and "
        "confidence intervals are labeled. Long-run solve rate gives every sequence equal "
        "weight; turn counts are shown separately. Matched work contains only one-shot "
        "cases and long-run turns solved by every reported column in the same round. Agent "
        "time excludes setup, validation, and judging. Cost, wall time per solve, and burn rate "
        "include all attempts. Active share is the union of model, tool, and completed own-job "
        "intervals divided by wall time; idle time is the remainder. Own-job wait counts only "
        "delivered jobs; stuck-job wait reports launched jobs without a completion. Longest "
        "silent gap is the largest contiguous idle interval and includes the count of records "
        "at or above five minutes. Codex model intervals run from task start, turn context, or "
        "completed tool output through the response's token-usage record; tool intervals pair "
        "function/custom-tool calls with outputs by call ID. Waste counts repeat plus filler "
        "calls over all tool calls. "
        "Tail is provider exit minus the final assistant message. Relative indexes divide each "
        "matched item by its across-column median, then take the per-column geometric mean "
        "(1.00 is typical); their 95% confidence intervals use 10,000 fixed-seed bootstrap "
        "resamples of paired matched item-round observations. With one column, every relative "
        "index is 1.00 by definition and becomes meaningful only when another column is added. "
        "Zero-valued items are excluded because log(0) is undefined, with exclusion counts "
        "reported in the table. Solve-rate confidence intervals are pooled Wilson 95% intervals. "
        "The efficiency-only headline is the geometric "
        "mean of matched-work relative cost and wall-time indexes; lower is better, and wall "
        "time already carries all waiting. Assisted turns remain in the scored totals; the "
        "protocol excludes only unscored turns, which ‘count toward neither solve rate nor "
        "efficiency.’ Unscored long-run turns are listed separately and excluded from solve, "
        "judge, efficiency, and matched-work metrics. Total tokens are "
        "fresh input + cache read + output, plus reasoning only where a client reports it "
        "separately; Codex output already includes its reasoning tokens. Missing client "
        "evidence is UNKNOWN, "
        "never zero. Judge mean is diagnostic only and covers one-shots: long-run judge "
        "prompts before 2026-10-17 listed changed paths without the diff. GOLD never merges "
        "solve and efficiency._",
    ])
    return "\n".join(lines)


def _write_marker_block(marker: str, report: str) -> None:
    marker_name = marker
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

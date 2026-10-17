"""Extract wall-clock efficiency metrics from retained client artifacts."""
from __future__ import annotations

import json
import math
import re
import shlex
import sqlite3
import statistics
import subprocess
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence


Interval = tuple[int, int]


@dataclass(frozen=True)
class EfficiencyMetrics:
    wall_ms: int
    model_ms: Optional[int]
    tool_ms: Optional[int]
    own_job_ms: Optional[int]
    stuck_wait_ms: Optional[int]
    busy_ms: Optional[int]
    idle_ms: Optional[int]
    longest_silent_gap_ms: Optional[int]
    tail_ms: Optional[int]
    tool_calls: Optional[int]
    repeat_calls: Optional[int]
    filler_calls: Optional[int]


@dataclass(frozen=True)
class _Call:
    name: str
    arguments: object
    output: object
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None


def union_duration_ms(intervals: Iterable[Interval]) -> int:
    ordered = sorted(intervals)
    if not ordered:
        return 0
    start, end = ordered[0]
    if end < start:
        raise ValueError(f"interval ends before it starts: {start}..{end}")
    total = 0
    for next_start, next_end in ordered[1:]:
        if next_end < next_start:
            raise ValueError(
                f"interval ends before it starts: {next_start}..{next_end}"
            )
        if next_start > end:
            total += end - start
            start, end = next_start, next_end
        else:
            end = max(end, next_end)
    return total + end - start


def _clamp_interval(interval: Interval, window: Interval) -> Optional[Interval]:
    start, end = interval
    window_start, window_end = window
    if end < start:
        raise ValueError(f"interval ends before it starts: {start}..{end}")
    if window_end < window_start:
        raise ValueError(f"run window ends before it starts: {window_start}..{window_end}")
    clamped_start = max(start, window_start)
    clamped_end = min(end, window_end)
    return (clamped_start, clamped_end) if clamped_end > clamped_start else None


def _clamp_intervals(intervals: Iterable[Interval], window: Interval) -> list[Interval]:
    return [
        clamped
        for interval in intervals
        if (clamped := _clamp_interval(interval, window)) is not None
    ]


def _subtract_intervals(
    intervals: Iterable[Interval], exclusions: Iterable[Interval]
) -> list[Interval]:
    remaining = list(intervals)
    for exclusion_start, exclusion_end in sorted(exclusions):
        next_remaining: list[Interval] = []
        for start, end in remaining:
            if exclusion_end <= start or exclusion_start >= end:
                next_remaining.append((start, end))
                continue
            if exclusion_start > start:
                next_remaining.append((start, exclusion_start))
            if exclusion_end < end:
                next_remaining.append((exclusion_end, end))
        remaining = next_remaining
    return remaining


def _longest_gap_ms(intervals: Iterable[Interval], window: Interval) -> int:
    window_start, window_end = window
    if window_end < window_start:
        raise ValueError(f"run window ends before it starts: {window_start}..{window_end}")
    ordered = sorted(_clamp_intervals(intervals, window))
    cursor = window_start
    longest = 0
    for start, end in ordered:
        if start > cursor:
            longest = max(longest, start - cursor)
        cursor = max(cursor, end)
    return max(longest, window_end - cursor)


def geometric_mean(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    if any(value <= 0 for value in values):
        return None
    return math.exp(sum(math.log(value) for value in values) / len(values))


def relative_indexes(
    values_by_column: Mapping[str, Mapping[str, Optional[float]]],
) -> tuple[dict[str, Optional[float]], int]:
    """Return per-column geometric indexes against each item's median."""
    ratios, excluded = relative_index_ratios(values_by_column)
    return (
        {
            label: None if column_ratios is None else geometric_mean(column_ratios)
            for label, column_ratios in ratios.items()
        },
        excluded,
    )


def relative_index_ratios(
    values_by_column: Mapping[str, Mapping[str, Optional[float]]],
) -> tuple[dict[str, Optional[list[float]]], int]:
    """Return paired item ratios used by ``relative_indexes``."""
    item_keys = sorted(
        {key for values in values_by_column.values() for key in values}
    )
    ratios: dict[str, list[float]] = {label: [] for label in values_by_column}
    unknown: set[str] = set()
    excluded = 0
    for key in item_keys:
        reported = [
            values[key]
            for values in values_by_column.values()
            if key in values and values[key] is not None
        ]
        if any(value < 0 for value in reported):
            raise ValueError(f"relative index item {key} has a negative value")
        if any(value == 0 for value in reported):
            excluded += 1
            continue
        if not reported:
            for label in values_by_column:
                unknown.add(label)
            continue
        median = statistics.median(reported)
        if median == 0:
            excluded += 1
            continue
        for label, values in values_by_column.items():
            value = values.get(key)
            if value is None:
                unknown.add(label)
            else:
                ratios[label].append(value / median)
    return {
        label: None if label in unknown else column_ratios
        for label, column_ratios in ratios.items()
    }, excluded


def _parse_timestamp(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{label} timestamp is not numeric or ISO-8601")
    if isinstance(value, (int, float)):
        number = float(value)
        return int(number * 1000) if number < 10_000_000_000 else int(number)
    if isinstance(value, str):
        try:
            return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
        except ValueError as exc:
            raise ValueError(f"{label} has invalid ISO-8601 timestamp: {value}") from exc
    raise TypeError(f"{label} timestamp is not numeric or ISO-8601")


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if not stripped or not stripped.startswith("{"):
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {path}:{line_no}: {exc}") from exc
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _canonical(value: object) -> str:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value
        value = decoded
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _process_timing(rows: Sequence[dict[str, Any]]) -> Optional[tuple[int, int]]:
    timing_rows = [row for row in rows if row.get("type") == "octobench_process_timing"]
    if not timing_rows:
        return None
    if len(timing_rows) != 1:
        raise ValueError(f"expected one process timing row, found {len(timing_rows)}")
    started = timing_rows[0].get("started_at_ms")
    ended = timing_rows[0].get("ended_at_ms")
    if not isinstance(started, int) or not isinstance(ended, int):
        raise TypeError("process timing start/end is not integer")
    if ended < started:
        raise ValueError(f"process timing ends before it starts: {started}..{ended}")
    return started, ended


def _run_window(
    process_timing: Optional[Interval], start_ms: int, wall_ms: int
) -> Interval:
    if process_timing is not None:
        return process_timing
    return start_ms, start_ms + wall_ms


def _tail_duration_ms(final_assistant_ms: int, window: Interval) -> int:
    start_ms, exit_ms = window
    clamped_final = min(max(final_assistant_ms, start_ms), exit_ms)
    return exit_ms - clamped_final


def _shell_command(arguments: object) -> Optional[str]:
    if isinstance(arguments, str):
        try:
            decoded = json.loads(arguments)
        except json.JSONDecodeError:
            return arguments
        arguments = decoded
    if not isinstance(arguments, dict):
        return None
    command = arguments.get("command")
    if command is None:
        command = arguments.get("cmd")
    if isinstance(command, list) and all(isinstance(part, str) for part in command):
        return shlex.join(command)
    return command if isinstance(command, str) else None


def _has_unquoted_shell_syntax(command: str) -> bool:
    if "$" in command or "`" in command or "\n" in command:
        return True
    quote: Optional[str] = None
    escaped = False
    for character in command:
        if escaped:
            escaped = False
            continue
        if character == "\\" and quote != "'":
            escaped = True
            continue
        if quote is not None:
            if character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
        elif character in "*?[{}|<>&;":
            return True
    return False


def is_filler_call(name: str, arguments: object) -> bool:
    normalized_name = name.lower().replace("-", "_")
    if not any(
        marker in normalized_name
        for marker in ("shell", "bash", "terminal", "exec_command", "command_execution")
    ):
        return False
    command = _shell_command(arguments)
    if command is None:
        return False
    stripped = command.strip()
    if stripped in {"true", ":"}:
        return True
    if _has_unquoted_shell_syntax(stripped):
        return False
    try:
        parts = shlex.split(stripped)
    except ValueError:
        return False
    if len(parts) == 2 and parts[0] == "sleep":
        return re.fullmatch(r"(?:\d+(?:\.\d+)?|\.\d+)", parts[1]) is not None
    if parts and parts[0] in {"echo", "printf"}:
        return len(parts) > 1
    return False


def _call_counts(
    calls: Sequence[_Call], incomplete: bool
) -> tuple[int, Optional[int], int]:
    seen: set[tuple[str, str, str]] = set()
    repeats = 0
    complete = True
    fillers = 0
    for call in calls:
        fillers += is_filler_call(call.name, call.arguments)
        if call.output is _MISSING:
            # A call cut off by the cap never returned, so it cannot be shown to
            # repeat an earlier one; in a finished run a missing output is broken data.
            if not incomplete:
                complete = False
            continue
        signature = (call.name, _canonical(call.arguments), _canonical(call.output))
        if signature in seen:
            repeats += 1
        else:
            seen.add(signature)
    return len(calls), repeats if complete else None, fillers


_MISSING = object()


def _metrics(
    wall_ms: int,
    *,
    incomplete: bool,
    model_ms: Optional[int],
    tool_ms: Optional[int],
    intervals: Optional[Sequence[Interval]],
    own_job_intervals: Optional[Sequence[Interval]],
    stuck_job_intervals: Optional[Sequence[Interval]],
    run_window: Optional[Interval],
    sum_fallback: bool,
    tail_ms: Optional[int],
    calls: Optional[Sequence[_Call]],
) -> EfficiencyMetrics:
    if wall_ms < 0:
        raise ValueError(f"wall_ms must be non-negative, got {wall_ms}")
    for label, value in (("model_ms", model_ms), ("tool_ms", tool_ms), ("tail_ms", tail_ms)):
        if value is not None and value < 0:
            raise ValueError(f"{label} must be non-negative, got {value}")
    own_job_ms = (
        union_duration_ms(own_job_intervals)
        if own_job_intervals is not None
        else None
    )
    stuck_wait_ms = (
        union_duration_ms(stuck_job_intervals)
        if stuck_job_intervals is not None
        else None
    )
    if intervals is not None and own_job_intervals is not None:
        busy_intervals = [*intervals, *own_job_intervals]
        busy_ms = min(union_duration_ms(busy_intervals), wall_ms)
        longest_silent_gap_ms = (
            _longest_gap_ms(busy_intervals, run_window)
            if run_window is not None
            else None
        )
    elif (
        sum_fallback
        and model_ms is not None
        and tool_ms is not None
        and own_job_ms is not None
        and not own_job_intervals
    ):
        busy_ms = min(model_ms + tool_ms + own_job_ms, wall_ms)
        longest_silent_gap_ms = None
    else:
        busy_ms = None
        longest_silent_gap_ms = None
    idle_ms = wall_ms - busy_ms if busy_ms is not None else None
    if calls is None:
        tool_calls = repeat_calls = filler_calls = None
    else:
        tool_calls, repeat_calls, filler_calls = _call_counts(calls, incomplete)
    return EfficiencyMetrics(
        wall_ms=wall_ms,
        model_ms=model_ms,
        tool_ms=tool_ms,
        own_job_ms=own_job_ms,
        stuck_wait_ms=stuck_wait_ms,
        busy_ms=busy_ms,
        idle_ms=idle_ms,
        longest_silent_gap_ms=longest_silent_gap_ms,
        tail_ms=tail_ms,
        tool_calls=tool_calls,
        repeat_calls=repeat_calls,
        filler_calls=filler_calls,
    )


def _record_root(record_dir: Path) -> tuple[Path, Optional[int]]:
    match = re.fullmatch(r"turn_(\d+)", record_dir.name)
    if match:
        return record_dir.parent.parent, int(match.group(1))
    return record_dir, None


_JOB_RESOURCE_RE = re.compile(r"octofs://jobs/([^\s\"'`<>]+)")
_JOB_PROMOTION_RE = re.compile(r"moved to background job [`']?([^\s`']+)")


def _background_job_id(row: Mapping[str, object]) -> Optional[str]:
    content = row.get("content")
    text = content if isinstance(content, str) else json.dumps(row, ensure_ascii=False)
    resource = _JOB_RESOURCE_RE.search(text)
    if resource:
        return resource.group(1)
    promotion = _JOB_PROMOTION_RE.search(text)
    if promotion:
        return promotion.group(1)
    if row.get("source_kind") == "background_job":
        for field in ("source_id", "job_id", "id"):
            value = row.get(field)
            if isinstance(value, str) and value:
                return value.removeprefix("octofs://jobs/")
        raise ValueError("Octomind background-job injection lacks a job identifier")
    return None


def _is_background_job_status_check(row: Mapping[str, object]) -> bool:
    if row.get("state") == "status_check":
        return True
    content = row.get("content")
    return (
        isinstance(content, str)
        and re.search(r"<background_job\b[^>]*\bstate=[\"']status_check[\"']", content)
        is not None
    )


def _octomind_job_intervals(
    rows: Sequence[dict[str, Any]], process_end_ms: int, run_window: Interval
) -> tuple[list[Interval], list[Interval]]:
    launched: dict[str, int] = {}
    delivered: dict[str, int] = {}
    for row in rows:
        job_id = _background_job_id(row)
        if job_id is None:
            continue
        timestamp = _parse_timestamp(row.get("timestamp"), "Octomind background job")
        content = row.get("content")
        is_launch = (
            row.get("role") == "tool"
            and row.get("name") == "shell"
            and isinstance(content, str)
            and "moved to background job" in content
        )
        is_delivery = (
            row.get("role") == "user"
            and isinstance(content, str)
            and "<background_job" in content
        ) or (
            row.get("type") == "injected"
            and row.get("source_kind") == "background_job"
        )
        is_delivery = is_delivery and not _is_background_job_status_check(row)
        if is_launch:
            if job_id in launched:
                raise ValueError(f"Octomind background job launched twice: {job_id}")
            launched[job_id] = timestamp
        elif is_delivery and job_id in launched and timestamp <= process_end_ms:
            delivered[job_id] = min(delivered.get(job_id, timestamp), timestamp)
    completed_intervals: list[Interval] = []
    stuck_intervals: list[Interval] = []
    for job_id, start_ms in launched.items():
        end_ms = delivered.get(job_id)
        if end_ms is None:
            stuck_intervals.append((start_ms, process_end_ms))
            continue
        if end_ms < start_ms:
            raise ValueError(
                f"Octomind background job {job_id} completed before launch"
            )
        completed_intervals.append((start_ms, end_ms))
    return (
        _clamp_intervals(completed_intervals, run_window),
        _clamp_intervals(stuck_intervals, run_window),
    )


def _chronological_octomind_rows(
    rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    chronological: list[dict[str, Any]] = []
    seen: set[str] = set()
    latest_timestamp: Optional[int] = None
    for row in rows:
        signature = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if signature in seen:
            continue
        seen.add(signature)
        raw_timestamp = row.get("timestamp")
        if raw_timestamp is not None:
            timestamp = _parse_timestamp(raw_timestamp, "Octomind session row")
            if latest_timestamp is not None and timestamp < latest_timestamp:
                continue
            latest_timestamp = timestamp
        chronological.append(row)
    return chronological


def _octomind_work_intervals(
    rows: Sequence[dict[str, Any]], run_window: Interval
) -> tuple[list[Interval], list[Interval]]:
    model_intervals: list[Interval] = []
    tool_intervals: list[Interval] = []
    pending_tools: dict[str, int] = {}
    previous_boundary: Optional[int] = None
    for row in rows:
        role = row.get("role")
        if role not in {"assistant", "user", "tool", "system"}:
            continue
        timestamp = _parse_timestamp(row.get("timestamp"), "Octomind work row")
        if role == "assistant":
            if previous_boundary is not None:
                model_intervals.append((previous_boundary, timestamp))
            tool_calls = row.get("tool_calls")
            if tool_calls is not None:
                if not isinstance(tool_calls, list):
                    raise TypeError("Octomind assistant tool_calls is not a list")
                for tool_call in tool_calls:
                    if not isinstance(tool_call, dict) or not isinstance(
                        tool_call.get("id"), str
                    ):
                        raise ValueError("Octomind assistant tool call lacks string id")
                    pending_tools[tool_call["id"]] = timestamp
            continue
        if role == "tool":
            tool_call_id = row.get("tool_call_id")
            if isinstance(tool_call_id, str) and tool_call_id in pending_tools:
                tool_intervals.append((pending_tools.pop(tool_call_id), timestamp))
        previous_boundary = timestamp
    return (
        _clamp_intervals(model_intervals, run_window),
        _clamp_intervals(tool_intervals, run_window),
    )


def _calls_from_events(
    rows: Sequence[dict[str, Any]],
    *,
    use_type: str,
    result_type: str,
    id_key: str,
    name_key: str,
    arguments_key: str,
    output_key: str,
) -> list[_Call]:
    pending: dict[str, tuple[str, object]] = {}
    ordered: list[tuple[str, str, object]] = []
    outputs: dict[str, object] = {}
    for row in rows:
        if row.get("type") == use_type:
            call_id = row.get(id_key)
            name = row.get(name_key)
            if not isinstance(call_id, str) or not isinstance(name, str):
                raise ValueError(f"{use_type} lacks string {id_key}/{name_key}")
            arguments = row.get(arguments_key)
            pending[call_id] = (name, arguments)
            ordered.append((call_id, name, arguments))
        elif row.get("type") == result_type:
            call_id = row.get(id_key)
            if isinstance(call_id, str):
                outputs[call_id] = row.get(output_key)
    return [
        _Call(name, arguments, outputs.get(call_id, _MISSING))
        for call_id, name, arguments in ordered
    ]


def extract_octomind(
    record_dir: Path,
    wall_ms: int,
    session_id: Optional[str] = None,
    artifact_turn_number: Optional[int] = None,
    incomplete: bool = False,
) -> EfficiencyMetrics:
    run_root, turn_number = _record_root(record_dir)
    raw_path = record_dir / "logs" / "provider.raw.jsonl"
    calls: Optional[list[_Call]] = None
    process_timing: Optional[tuple[int, int]] = None
    if raw_path.is_file():
        raw_rows = _jsonl(raw_path)
        process_timing = _process_timing(raw_rows)
        calls = _calls_from_events(
            raw_rows,
            use_type="tool_use",
            result_type="tool_result",
            id_key="tool_id",
            name_key="tool",
            arguments_key="params",
            output_key="content",
        )

    session_dir = run_root / "state" / "octomind" / "sessions"
    sessions = sorted(session_dir.glob("*.jsonl.zst")) if session_dir.is_dir() else []
    if session_id is not None:
        sessions = [path for path in sessions if path.name == f"{session_id}.jsonl.zst"]
    # Without the retained compressed session, provider.raw.jsonl has events
    # but no timestamps for model, tool, or background-job intervals.
    if not sessions:
        return _metrics(
            wall_ms,
            incomplete=incomplete,
            model_ms=None,
            tool_ms=None,
            intervals=None,
            own_job_intervals=None,
            stuck_job_intervals=None,
            run_window=None,
            sum_fallback=False,
            tail_ms=None,
            calls=calls,
        )
    if len(sessions) != 1:
        raise ValueError(
            f"expected one Octomind session under {session_dir}, found {len(sessions)}"
        )
    proc = subprocess.run(
        ["zstd", "-dcq", str(sessions[0])],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ValueError(f"cannot decompress Octomind session {sessions[0]}: {proc.stderr.strip()}")
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(proc.stdout.splitlines(), 1):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {sessions[0]}:{line_no}: {exc}") from exc
        if isinstance(value, dict):
            rows.append(value)

    target_turn = artifact_turn_number or turn_number or 1
    summaries: list[tuple[int, dict[str, Any]]] = []
    for index, row in enumerate(rows):
        if row.get("type") != "SUMMARY":
            continue
        info = row.get("session_info")
        timing = info.get("turn_timing") if isinstance(info, dict) else None
        if not isinstance(timing, dict) or not isinstance(timing.get("completed"), int):
            raise ValueError("Octomind SUMMARY lacks session_info.turn_timing.completed")
        summaries.append((index, row))
    target = next(
        (
            (index, row)
            for index, row in summaries
            if row["session_info"]["turn_timing"]["completed"] == target_turn
        ),
        None,
    )
    if target is None and not incomplete:
        raise ValueError(f"Octomind session has no completed turn {target_turn}")
    target_index, target_row = target if target is not None else (len(rows), None)
    previous = [
        (index, row)
        for index, row in summaries
        if index < target_index
        and row["session_info"]["turn_timing"]["completed"] == target_turn - 1
    ]
    previous_index, previous_row = previous[-1] if previous else (-1, None)

    def cumulative(row: Optional[dict[str, Any]], field: str) -> int:
        if row is None:
            return 0
        value = row["session_info"].get(field)
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"Octomind SUMMARY session_info.{field} is not an integer")
        return value

    record_rows = _chronological_octomind_rows(
        rows[previous_index + 1 : target_index]
    )
    if target_row is not None:
        process_end = (
            process_timing[1]
            if process_timing is not None
            else _parse_timestamp(target_row.get("timestamp"), "Octomind SUMMARY")
        )
        run_window = (
            process_timing
            if process_timing is not None
            else (process_end - wall_ms, process_end)
        )
        model_ms = cumulative(target_row, "total_api_time_ms") - cumulative(
            previous_row, "total_api_time_ms"
        )
        tool_ms = cumulative(target_row, "total_tool_time_ms") - cumulative(
            previous_row, "total_tool_time_ms"
        )
    else:
        record_start = (
            _parse_timestamp(previous_row.get("timestamp"), "Octomind turn start")
            if previous_row is not None
            else next(
                (
                    _parse_timestamp(row.get("timestamp"), "Octomind turn start")
                    for row in record_rows
                    if row.get("timestamp") is not None
                ),
                0,
            )
        )
        run_window = _run_window(process_timing, record_start, wall_ms)
        process_end = run_window[1]
        model_ms = None
        tool_ms = None
    model_intervals, tool_intervals = _octomind_work_intervals(
        record_rows, run_window
    )
    if target_row is None:
        tool_ms = union_duration_ms(tool_intervals)
    final_assistant = next(
        (
            row
            for row in reversed(record_rows)
            if row.get("role") == "assistant"
            and isinstance(row.get("content"), str)
            and row["content"].strip()
        ),
        None,
    )
    own_job_intervals, stuck_job_intervals = _octomind_job_intervals(
        record_rows, process_end, run_window
    )
    tail_ms = None
    if final_assistant is not None and target_row is not None:
        tail_ms = _tail_duration_ms(
            _parse_timestamp(
                final_assistant.get("timestamp"), "Octomind final assistant"
            ),
            (run_window[0], process_end),
        )
    return _metrics(
        wall_ms,
        incomplete=incomplete,
        model_ms=model_ms,
        tool_ms=tool_ms,
        intervals=[*model_intervals, *tool_intervals],
        own_job_intervals=own_job_intervals,
        stuck_job_intervals=stuck_job_intervals,
        run_window=run_window,
        sum_fallback=False,
        tail_ms=tail_ms,
        calls=calls,
    )


def _open_db(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def extract_opencode(
    record_dir: Path,
    wall_ms: int,
    session_id: Optional[str] = None,
    artifact_turn_number: Optional[int] = None,
    incomplete: bool = False,
) -> EfficiencyMetrics:
    run_root, turn_number = _record_root(record_dir)
    db_path = run_root / "state" / "opencode" / "opencode.db"
    raw_path = record_dir / "logs" / "provider.raw.jsonl"
    process_timing = _process_timing(_jsonl(raw_path)) if raw_path.is_file() else None
    # provider.raw.jsonl does not contain outputs for every call; without the
    # retained opencode.db neither timing nor repeat-call equality is knowable.
    if not db_path.is_file():
        return _metrics(
            wall_ms,
            incomplete=incomplete,
            model_ms=None,
            tool_ms=None,
            intervals=None,
            own_job_intervals=[],
            stuck_job_intervals=[],
            run_window=process_timing,
            sum_fallback=False,
            tail_ms=None,
            calls=None,
        )
    with closing(_open_db(db_path)) as db:
        if session_id is None:
            roots = db.execute(
                "SELECT id FROM session WHERE parent_id IS NULL ORDER BY time_created"
            ).fetchall()
            if len(roots) != 1:
                raise ValueError(
                    f"expected one OpenCode root session in {db_path}, found {len(roots)}"
                )
            session_id = roots[0][0]
        session = db.execute(
            "SELECT time_updated FROM session WHERE id = ?", (session_id,)
        ).fetchone()
        if session is None:
            raise ValueError(f"OpenCode session not found: {session_id}")
        user_rows = db.execute(
            "SELECT id, time_created, data FROM message WHERE session_id = ? "
            "ORDER BY time_created, id",
            (session_id,),
        ).fetchall()

        def is_turn_prompt(message_id: str, raw: str) -> bool:
            if json.loads(raw).get("role") != "user":
                return False
            parts = db.execute(
                "SELECT data FROM part WHERE message_id = ?", (message_id,)
            ).fetchall()
            return any(
                part.get("type") == "text" and not part.get("synthetic")
                for part in (json.loads(data) for (data,) in parts)
            )

        # Compaction adds a `compaction` user message and a synthetic "Continue"
        # prompt; counting those as turns shifts every later turn's window.
        user_starts = [
            created
            for message_id, created, raw in user_rows
            if is_turn_prompt(message_id, raw)
        ]
        target_turn = artifact_turn_number or turn_number or 1
        if len(user_starts) < target_turn:
            raise ValueError(f"OpenCode session has no user message for turn {target_turn}")
        start_ms = user_starts[target_turn - 1]
        run_window = _run_window(process_timing, start_ms, wall_ms)
        end_exclusive = (
            user_starts[target_turn]
            if len(user_starts) > target_turn
            else run_window[1] + 1
        )
        tree_sql = """
            WITH RECURSIVE session_tree(id) AS (
                SELECT id FROM session WHERE id = ?
                UNION ALL
                SELECT session.id
                FROM session JOIN session_tree ON session.parent_id = session_tree.id
            )
        """
        message_rows = db.execute(
            tree_sql
            + """
            SELECT message.session_id, message.data
            FROM message JOIN session_tree ON message.session_id = session_tree.id
            WHERE message.time_created >= ? AND message.time_created < ?
            ORDER BY message.time_created, message.id
            """,
            (session_id, start_ms, end_exclusive),
        ).fetchall()
        part_rows = db.execute(
            tree_sql
            + """
            SELECT part.session_id, part.data
            FROM part JOIN session_tree ON part.session_id = session_tree.id
            WHERE part.time_created >= ? AND part.time_created < ?
            ORDER BY part.time_created, part.id
            """,
            (session_id, start_ms, end_exclusive),
        ).fetchall()

    assistant_intervals: dict[str, list[Interval]] = {}
    for message_session_id, raw in message_rows:
        data = json.loads(raw)
        if data.get("role") != "assistant":
            continue
        timing = data.get("time")
        if not isinstance(timing, dict):
            raise ValueError("OpenCode assistant message lacks time")
        created = timing.get("created")
        completed = timing.get("completed")
        if not isinstance(created, int):
            raise TypeError("OpenCode assistant time.created/completed is not integer")
        if not isinstance(completed, int):
            if not incomplete:
                raise TypeError("OpenCode assistant time.created/completed is not integer")
            completed = run_window[1]
        clamped = _clamp_interval((created, completed), run_window)
        if clamped is not None:
            assistant_intervals.setdefault(message_session_id, []).append(clamped)

    calls: list[_Call] = []
    all_tool_intervals: dict[str, list[Interval]] = {}
    real_tool_intervals: list[Interval] = []
    final_text_end: Optional[int] = None
    for part_session_id, raw in part_rows:
        data = json.loads(raw)
        typ = data.get("type")
        if typ == "tool":
            state = data.get("state")
            if not isinstance(state, dict):
                raise ValueError("OpenCode tool part lacks state")
            timing = state.get("time")
            start = timing.get("start") if isinstance(timing, dict) else None
            end = timing.get("end") if isinstance(timing, dict) else None
            if not isinstance(start, int):
                raise TypeError("OpenCode tool state.time.start/end is not integer")
            if not isinstance(end, int):
                if not incomplete:
                    raise TypeError("OpenCode tool state.time.start/end is not integer")
                end = run_window[1]
            clamped = _clamp_interval((start, end), run_window)
            if clamped is not None:
                all_tool_intervals.setdefault(part_session_id, []).append(clamped)
                if str(data.get("tool", "")).lower() != "task":
                    real_tool_intervals.append(clamped)
            calls.append(
                _Call(
                    str(data.get("tool", "")),
                    state.get("input"),
                    state["output"] if "output" in state else state.get("error", _MISSING),
                    clamped[0] if clamped is not None else None,
                    clamped[1] if clamped is not None else None,
                )
            )
        elif typ == "text" and part_session_id == session_id:
            timing = data.get("time")
            if isinstance(timing, dict) and isinstance(timing.get("end"), int):
                final_text_end = timing["end"]

    model_intervals = [
        interval
        for assistant_session_id, intervals in assistant_intervals.items()
        for interval in _subtract_intervals(
            intervals, all_tool_intervals.get(assistant_session_id, [])
        )
    ]
    model_ms = union_duration_ms(model_intervals)
    tool_ms = union_duration_ms(real_tool_intervals)
    tail_ms = (
        _tail_duration_ms(final_text_end, run_window)
        if process_timing is not None and final_text_end is not None
        else None
    )
    return _metrics(
        wall_ms,
        incomplete=incomplete,
        model_ms=model_ms,
        tool_ms=tool_ms,
        intervals=[*model_intervals, *real_tool_intervals],
        own_job_intervals=[],
        stuck_job_intervals=[],
        run_window=run_window,
        sum_fallback=False,
        tail_ms=tail_ms,
        calls=calls,
    )


def extract_claude(
    record_dir: Path, wall_ms: int, incomplete: bool = False
) -> EfficiencyMetrics:
    raw_path = record_dir / "logs" / "provider.raw.jsonl"
    if not raw_path.is_file():
        # Claude timing and call equality both live in provider.raw.jsonl.
        return _metrics(
            wall_ms,
            incomplete=incomplete,
            model_ms=None,
            tool_ms=None,
            intervals=None,
            own_job_intervals=[],
            stuck_job_intervals=[],
            run_window=None,
            sum_fallback=False,
            tail_ms=None,
            calls=None,
        )
    rows = _jsonl(raw_path)
    uses: dict[str, tuple[str, object, int]] = {}
    ordered: list[str] = []
    outputs: dict[str, tuple[object, int]] = {}
    final_assistant_ms: Optional[int] = None
    result: Optional[dict[str, Any]] = None
    process_timing: Optional[tuple[int, int]] = None
    events: list[tuple[str, int]] = []
    for row in rows:
        typ = row.get("type")
        if typ == "assistant":
            timestamp = _parse_timestamp(row.get("timestamp"), "Claude assistant")
            events.append(("assistant", timestamp))
            content = (row.get("message") or {}).get("content") or []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    call_id = block.get("id")
                    name = block.get("name")
                    if not isinstance(call_id, str) or not isinstance(name, str):
                        raise ValueError("Claude tool_use lacks string id/name")
                    uses[call_id] = (name, block.get("input"), timestamp)
                    ordered.append(call_id)
                elif block.get("type") == "text" and str(block.get("text", "")).strip():
                    final_assistant_ms = timestamp
        elif typ == "user":
            timestamp = _parse_timestamp(row.get("timestamp"), "Claude user")
            events.append(("user", timestamp))
            for block in (row.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    call_id = block.get("tool_use_id")
                    if isinstance(call_id, str):
                        outputs[call_id] = (block.get("content"), timestamp)
        elif typ == "result":
            result = row
        elif typ == "octobench_process_timing":
            process_timing = _process_timing([row])
    if result is None and not incomplete:
        raise ValueError("Claude stream has no result event")
    model_ms = result.get("duration_api_ms") if result is not None else None
    if model_ms is not None and not isinstance(model_ms, int):
        raise TypeError("Claude result.duration_api_ms is not integer")
    if result is not None and model_ms is None:
        raise TypeError("Claude result.duration_api_ms is not integer")
    event_times = [timestamp for _role, timestamp in events]
    record_start = min(event_times) if event_times else (process_timing or (0, 0))[0]
    run_window = _run_window(process_timing, record_start, wall_ms)
    model_intervals: list[Interval] = []
    previous_event = run_window[0]
    for role, timestamp in events:
        if role == "assistant":
            clamped = _clamp_interval((previous_event, timestamp), run_window)
            if clamped is not None:
                model_intervals.append(clamped)
        previous_event = timestamp
    calls: list[_Call] = []
    call_intervals: list[Interval] = []
    complete_tool_timing = True
    for call_id in ordered:
        output, end = outputs.get(call_id, (_MISSING, None))
        start = uses[call_id][2]
        if end is None and incomplete:
            end = run_window[1]
        if end is None:
            complete_tool_timing = False
            clamped = None
        else:
            clamped = _clamp_interval((start, end), run_window)
            if clamped is not None:
                call_intervals.append(clamped)
        calls.append(
            _Call(
                uses[call_id][0],
                uses[call_id][1],
                output,
                clamped[0] if clamped is not None else None,
                clamped[1] if clamped is not None else None,
            )
        )
    tool_ms = (
        union_duration_ms(call_intervals)
        if complete_tool_timing
        else None
    )
    tail_ms = None
    if final_assistant_ms is not None and process_timing is not None:
        tail_ms = _tail_duration_ms(final_assistant_ms, run_window)
    return _metrics(
        wall_ms,
        incomplete=incomplete,
        model_ms=model_ms,
        tool_ms=tool_ms,
        intervals=(
            [*model_intervals, *call_intervals]
            if complete_tool_timing
            else None
        ),
        own_job_intervals=[],
        stuck_job_intervals=[],
        run_window=run_window,
        sum_fallback=False,
        tail_ms=tail_ms,
        calls=calls,
    )


_CODEX_NON_TOOL_ITEM_TYPES = {"agent_message", "reasoning"}


def _codex_item_arguments(item: Mapping[str, object]) -> object:
    for key in ("command", "arguments", "input", "query"):
        if key in item:
            return item[key]
    return {
        key: value
        for key, value in item.items()
        if key not in {"id", "type", "status", "aggregated_output", "result", "output"}
    }


def _codex_item_output(item: Mapping[str, object]) -> object:
    for key in ("aggregated_output", "result", "output"):
        if key in item:
            return item[key]
    return {
        key: value
        for key, value in item.items()
        if key not in {"id", "type", "command", "arguments", "input", "query"}
    }


def _codex_raw_calls(
    path: Path,
) -> tuple[Optional[list[_Call]], Optional[tuple[int, int]]]:
    if not path.is_file():
        return None, None
    starts: dict[str, tuple[str, object]] = {}
    ordered: list[str] = []
    outputs: dict[str, object] = {}
    rows = _jsonl(path)
    process_timing = _process_timing(rows)
    for row in rows:
        if row.get("type") == "octobench_process_timing":
            continue
        item = row.get("item")
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str):
            continue
        item_type = item.get("type")
        if (
            row.get("type") == "item.started"
            and isinstance(item_type, str)
            and item_type not in _CODEX_NON_TOOL_ITEM_TYPES
        ):
            starts[item_id] = (item_type, _codex_item_arguments(item))
            ordered.append(item_id)
        elif row.get("type") == "item.completed" and item_id in starts:
            outputs[item_id] = _codex_item_output(item)
    return (
        [
            _Call(starts[item_id][0], starts[item_id][1], outputs.get(item_id, _MISSING))
            for item_id in ordered
        ],
        process_timing,
    )


def _codex_rollout_paths(record_dir: Path, session_id: Optional[str]) -> list[Path]:
    rollout_path = record_dir / "logs" / "codex.rollout.jsonl"
    has_local_rollout = rollout_path.is_file()
    run_root, _turn_number = _record_root(record_dir)
    candidates = sorted((run_root / "state" / "codex").glob("**/rollout-*.jsonl"))
    if session_id is not None:
        candidates = [path for path in candidates if session_id in path.name]
    if len(candidates) > 1 and not has_local_rollout:
        raise ValueError(
            f"expected one Codex rollout under {run_root / 'state' / 'codex'}, "
            f"found {len(candidates)}"
        )
    paths = [rollout_path] if has_local_rollout else []
    if len(candidates) > 1:
        candidates = []
    if candidates and candidates[0] not in paths:
        paths.append(candidates[0])
    return paths


def extract_codex(
    record_dir: Path,
    wall_ms: int,
    session_id: Optional[str] = None,
    incomplete: bool = False,
) -> EfficiencyMetrics:
    raw_calls, process_timing = _codex_raw_calls(
        record_dir / "logs" / "provider.raw.jsonl"
    )
    # Codex provider stdout events have no timestamps. August 2026 one-shots therefore
    # keep call counts but timing is UNKNOWN; current runs retain this rollout.
    rollout_paths = _codex_rollout_paths(record_dir, session_id)
    if not rollout_paths:
        return _metrics(
            wall_ms,
            incomplete=incomplete,
            model_ms=None,
            tool_ms=None,
            intervals=None,
            own_job_intervals=[],
            stuck_job_intervals=[],
            run_window=process_timing,
            sum_fallback=False,
            tail_ms=None,
            calls=raw_calls,
        )
    if process_timing is None:
        rows = _jsonl(rollout_paths[0])
        task_starts = [
            _parse_timestamp(row.get("timestamp"), "Codex task start")
            for row in rows
            if row.get("type") == "event_msg"
            and isinstance(row.get("payload"), dict)
            and row["payload"].get("type") == "task_started"
        ]
        if len(task_starts) != 1:
            return _metrics(
                wall_ms,
                incomplete=incomplete,
                model_ms=None,
                tool_ms=None,
                intervals=None,
                own_job_intervals=[],
                stuck_job_intervals=[],
                run_window=None,
                sum_fallback=False,
                tail_ms=None,
                calls=raw_calls,
            )
        run_window = _run_window(None, task_starts[0], wall_ms)
    else:
        run_window = process_timing

    rows = []
    for rollout_path in rollout_paths:
        candidate_rows = [
            row
            for row in _jsonl(rollout_path)
            if row.get("timestamp") is not None
            and run_window[0]
            <= _parse_timestamp(row["timestamp"], "Codex rollout row")
            <= run_window[1]
        ]
        if candidate_rows:
            rows = candidate_rows
            break
    if not rows:
        return _metrics(
            wall_ms,
            incomplete=incomplete,
            model_ms=None,
            tool_ms=None,
            intervals=None,
            own_job_intervals=[],
            stuck_job_intervals=[],
            run_window=run_window,
            sum_fallback=False,
            tail_ms=None,
            calls=raw_calls,
        )
    pending: dict[str, tuple[str, object, int]] = {}
    ordered: list[str] = []
    outputs: dict[str, tuple[object, int]] = {}
    final_assistant_ms: Optional[int] = None
    model_intervals: list[Interval] = []
    model_start: Optional[int] = None
    complete_model_timing = True
    active: set[str] = set()
    for row in rows:
        timestamp = _parse_timestamp(row.get("timestamp"), "Codex rollout row")
        payload = row.get("payload")
        typ = payload.get("type") if isinstance(payload, dict) else None
        if row.get("type") == "event_msg" and typ == "task_started":
            if model_start is not None:
                complete_model_timing = False
            model_start = timestamp
        elif row.get("type") == "turn_context" and model_start is None and not active:
            model_start = timestamp
        elif row.get("type") == "token_usage_record":
            if model_start is None:
                complete_model_timing = False
            else:
                model_intervals.append((model_start, timestamp))
                model_start = None
        elif not isinstance(payload, dict):
            continue
        if typ in {"function_call", "custom_tool_call"}:
            call_id = payload.get("call_id")
            name = payload.get("name")
            if not isinstance(call_id, str) or not isinstance(name, str):
                raise ValueError("Codex tool call lacks string call_id/name")
            active.add(call_id)
            arguments = payload.get("arguments", payload.get("input"))
            pending[call_id] = (name, arguments, timestamp)
            ordered.append(call_id)
        elif typ in {"function_call_output", "custom_tool_call_output"}:
            call_id = payload.get("call_id")
            if isinstance(call_id, str) and call_id in pending:
                outputs[call_id] = (payload.get("output"), timestamp)
                active.discard(call_id)
                if not active:
                    if model_start is not None:
                        complete_model_timing = False
                    model_start = timestamp
        elif typ == "message" and payload.get("role") == "assistant":
            phase = payload.get("phase")
            if phase in {None, "final_answer"}:
                final_assistant_ms = timestamp
    complete_tool_timing = not active
    if active and incomplete:
        # Killed mid-tool: the call ran until the cap ended the process.
        for call_id in active:
            outputs[call_id] = (_MISSING, run_window[1])
        complete_tool_timing = True
    if model_start is not None:
        if incomplete:
            model_intervals.append((model_start, run_window[1]))
        else:
            complete_model_timing = False
    model_intervals = _clamp_intervals(model_intervals, run_window)
    tool_intervals = _clamp_intervals([
        (pending[call_id][2], outputs[call_id][1])
        for call_id in ordered
        if call_id in outputs
    ], run_window)
    calls = [
        _Call(
            pending[call_id][0],
            pending[call_id][1],
            outputs.get(call_id, (_MISSING, None))[0],
            pending[call_id][2],
            outputs.get(call_id, (_MISSING, None))[1],
        )
        for call_id in ordered
    ]
    return _metrics(
        wall_ms,
        incomplete=incomplete,
        model_ms=(
            sum(end - start for start, end in model_intervals)
            if complete_model_timing
            else None
        ),
        tool_ms=(
            sum(end - start for start, end in tool_intervals)
            if complete_tool_timing
            else None
        ),
        intervals=(
            [*model_intervals, *tool_intervals]
            if complete_model_timing and complete_tool_timing
            else None
        ),
        own_job_intervals=[],
        stuck_job_intervals=[],
        run_window=run_window,
        sum_fallback=False,
        tail_ms=(
            _tail_duration_ms(final_assistant_ms, run_window)
            if process_timing is not None and final_assistant_ms is not None
            else None
        ),
        calls=calls,
    )


def extract_efficiency(
    provider: str,
    record_dir: Path,
    wall_ms: int,
    session_id: Optional[str] = None,
    artifact_turn_number: Optional[int] = None,
    status: Optional[str] = None,
) -> EfficiencyMetrics:
    extractors = {
        "octomind": extract_octomind,
        "opencode": extract_opencode,
        "claude": extract_claude,
        "codex": extract_codex,
    }
    try:
        extractor = extractors[provider]
    except KeyError as exc:
        raise ValueError(f"unsupported efficiency provider: {provider}") from exc
    incomplete = status in {"killed_by_case_cap", "killed_by_sequence_cap"}
    if provider == "opencode":
        return extract_opencode(
            record_dir, wall_ms, session_id, artifact_turn_number, incomplete
        )
    if provider == "octomind":
        return extract_octomind(
            record_dir, wall_ms, session_id, artifact_turn_number, incomplete
        )
    if provider == "codex":
        return extract_codex(record_dir, wall_ms, session_id, incomplete)
    return extractor(record_dir, wall_ms, incomplete)

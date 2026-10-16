"""Build the evidence inventory used to choose a future GOLD suite.

The inventory joins current one-shot and long-run manifests to the historical
per-case tables in BENCHMARK.md. It deliberately ranks evidence but does not
select any cases.
"""
from __future__ import annotations

import ast
import csv
import json
import math
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_PATH = REPO_ROOT / "BENCHMARK.md"
ONESHOT_ROOT = REPO_ROOT / "cases" / "dev" / "oneshot"
LONGRUN_ROOT = REPO_ROOT / "cases" / "dev" / "longrun"
OUTPUT_DIR = REPO_ROOT / "docs" / "gold"
UNKNOWN = "UNKNOWN"

ONESHOT_LIST_FIELDS = ("failure_modes", "capability_tags")
ONESHOT_SCALAR_FIELDS = (
    "task_type",
    "prompt_style",
    "spec_level",
    "test_visibility",
)
TURN_LIST_FIELDS = ONESHOT_LIST_FIELDS
TURN_SCALAR_FIELDS = ("difficulty",) + ONESHOT_SCALAR_FIELDS

QUANTITY_RE = re.compile(r"(?P<number>\d+(?:\.\d+)?)(?P<suffix>[KM]?)")
ONESHOT_CELL_RE = re.compile(
    r"(?P<verdict>PASS|FAIL|INFRA|LEAK|FAIL\+LEAK|INFRA\+LEAK) "
    r"j=(?P<judge>\?|\d+(?:\.\d+)?) "
    r"\$(?P<cost>\?|\d+(?:\.\d+)?) "
    r"(?P<minutes>\d+(?:\.\d+)?)m · "
    r"(?P<steps>\d+) steps · "
    r"(?P<fresh>\d+(?:\.\d+)?[KM]?) tok "
    r"\((?P<input>\d+(?:\.\d+)?[KM]?)/"
    r"(?P<output>\d+(?:\.\d+)?[KM]?)/"
    r"(?P<reasoning>\d+(?:\.\d+)?[KM]?)\) · "
    r"(?P<cache>\d+(?:\.\d+)?[KM]?) cache"
)
SEQUENCE_CELL_RE = re.compile(
    r"(?P<passed>\d+)/(?P<turns>\d+) "
    r"Σ(?P<score>\d+(?:\.\d+)?) "
    r"\$(?P<cost>\d+(?:\.\d+)?) "
    r"(?P<tokens>\d+(?:\.\d+)?[KM]?) "
    r"(?P<minutes>\d+(?:\.\d+)?)m"
)


@dataclass(frozen=True)
class OneShotCell:
    raw: str
    verdict: str
    judge: Optional[float]
    cost: Optional[float]
    minutes: Optional[float]
    steps: Optional[int]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    reasoning_tokens: Optional[int]
    cache_read: Optional[int]

    @property
    def total_tokens(self) -> Optional[int]:
        values = (
            self.input_tokens,
            self.output_tokens,
            self.reasoning_tokens,
            self.cache_read,
        )
        if any(value is None for value in values):
            return None
        return sum(value for value in values if value is not None)


@dataclass(frozen=True)
class SequenceCell:
    raw: str
    passed: int
    turns: int
    score: float
    cost: float
    tokens: int
    minutes: float


@dataclass(frozen=True)
class OneShotManifest:
    path: str
    case_id: str
    lang: str
    repo: str
    difficulty: str
    task_type: str
    failure_modes: Tuple[str, ...]
    prompt_style: str
    spec_level: str
    test_visibility: str
    capability_tags: Tuple[str, ...]
    verified: Optional[str]
    merged_at: Optional[str]
    instruction_words: int


@dataclass(frozen=True)
class SequenceManifest:
    path: str
    sequence_id: str
    lang: str
    repo: str
    verified: Optional[str]
    turns: Tuple[Dict[str, object], ...]


def _strip_yaml_comment(value: str) -> str:
    quote: Optional[str] = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote == '"':
            escaped = True
            continue
        if char in {"'", '"'}:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            continue
        if char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.rstrip()


def _parse_yaml_scalar(raw: str, source: Path, field: str) -> str:
    value = _strip_yaml_comment(raw).strip()
    if not value:
        raise ValueError(f"{source}: empty scalar for {field}")
    if value[0] in {"'", '"'}:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise ValueError(f"{source}: invalid quoted scalar for {field}: {value}") from exc
        if not isinstance(parsed, str):
            raise ValueError(f"{source}: non-string scalar for {field}: {value}")
        return parsed
    return value


def _mapping_matches(lines: Sequence[str], indent: int, key: str) -> List[Tuple[int, str]]:
    pattern = re.compile(rf"^{' ' * indent}{re.escape(key)}:\s*(.*)$")
    matches = []
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            matches.append((index, match.group(1)))
    return matches


def _mapping_scalar(
    lines: Sequence[str],
    indent: int,
    key: str,
    source: Path,
    required: bool = True,
) -> Optional[str]:
    matches = _mapping_matches(lines, indent, key)
    if not matches:
        if required:
            raise ValueError(f"{source}: missing {key}")
        return None
    if len(matches) != 1:
        raise ValueError(f"{source}: duplicate {key}")
    return _parse_yaml_scalar(matches[0][1], source, key)


def _parse_inline_list(raw: str, source: Path, field: str) -> Tuple[str, ...]:
    value = _strip_yaml_comment(raw).strip()
    if not (value.startswith("[") and value.endswith("]")):
        raise ValueError(f"{source}: invalid inline list for {field}: {value}")
    body = value[1:-1].strip()
    if not body:
        return ()
    parsed = next(csv.reader([body], skipinitialspace=True))
    return tuple(_parse_yaml_scalar(item, source, field) for item in parsed)


def _mapping_list(
    lines: Sequence[str], indent: int, key: str, source: Path
) -> Tuple[str, ...]:
    matches = _mapping_matches(lines, indent, key)
    if not matches:
        raise ValueError(f"{source}: missing {key}")
    if len(matches) != 1:
        raise ValueError(f"{source}: duplicate {key}")
    index, raw = matches[0]
    if _strip_yaml_comment(raw).strip():
        return _parse_inline_list(raw, source, key)

    values = []
    item_re = re.compile(rf"^{' ' * (indent + 2)}-\s+(.+)$")
    for line in lines[index + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        match = item_re.match(line)
        if match:
            values.append(_parse_yaml_scalar(match.group(1), source, key))
    if not values:
        raise ValueError(f"{source}: empty block list for {key}")
    return tuple(values)


def _section(lines: Sequence[str], indent: int, key: str, source: Path) -> Sequence[str]:
    matches = _mapping_matches(lines, indent, key)
    if len(matches) != 1:
        reason = "missing" if not matches else "duplicate"
        raise ValueError(f"{source}: {reason} {key} section")
    start, raw = matches[0]
    if _strip_yaml_comment(raw).strip():
        raise ValueError(f"{source}: {key} must be a block mapping")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            end = index
            break
    return lines[start + 1 : end]


def _literal_block(lines: Sequence[str], indent: int, key: str, source: Path) -> str:
    matches = _mapping_matches(lines, indent, key)
    if len(matches) != 1:
        reason = "missing" if not matches else "duplicate"
        raise ValueError(f"{source}: {reason} {key}")
    start, raw = matches[0]
    marker = _strip_yaml_comment(raw).strip()
    if marker not in {"|", "|-", "|+", ">", ">-", ">+"}:
        raise ValueError(f"{source}: {key} must use a YAML block scalar")
    content = []
    content_indent = indent + 2
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        if not line.strip():
            content.append("")
        elif line.startswith(" " * content_indent):
            content.append(line[content_indent:])
        else:
            raise ValueError(f"{source}: malformed indentation in {key}")
    if not content:
        raise ValueError(f"{source}: empty {key}")
    return "\n".join(content)


def _parse_oneshot_manifest(path: Path) -> OneShotManifest:
    lines = path.read_text(encoding="utf-8").splitlines()
    meta = _section(lines, 0, "meta", path)
    relative = path.parent.relative_to(REPO_ROOT / "cases").as_posix()
    return OneShotManifest(
        path=relative,
        case_id=_mapping_scalar(lines, 0, "id", path) or "",
        lang=path.parent.parent.name,
        repo=_mapping_scalar(meta, 2, "repo", path) or "",
        difficulty=_mapping_scalar(lines, 0, "difficulty", path) or "",
        task_type=_mapping_scalar(meta, 2, "task_type", path) or "",
        failure_modes=_mapping_list(meta, 2, "failure_modes", path),
        prompt_style=_mapping_scalar(meta, 2, "prompt_style", path) or "",
        spec_level=_mapping_scalar(meta, 2, "spec_level", path) or "",
        test_visibility=_mapping_scalar(meta, 2, "test_visibility", path) or "",
        capability_tags=_mapping_list(meta, 2, "capability_tags", path),
        verified=_mapping_scalar(meta, 2, "verified", path, required=False),
        merged_at=_mapping_scalar(meta, 2, "merged_at", path, required=False),
        instruction_words=len(_literal_block(lines, 0, "instruction", path).split()),
    )


def _turn_blocks(lines: Sequence[str], source: Path) -> List[Sequence[str]]:
    turns = _section(lines, 0, "turns", source)
    starts = [
        index for index, line in enumerate(turns) if re.match(r"^  - [A-Za-z_][\w-]*:", line)
    ]
    if not starts:
        raise ValueError(f"{source}: turns section is empty")
    blocks = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(turns)
        blocks.append(turns[start:end])
    return blocks


def _parse_sequence_manifest(path: Path) -> SequenceManifest:
    lines = path.read_text(encoding="utf-8").splitlines()
    meta = _section(lines, 0, "meta", path)
    turns = []
    for number, block in enumerate(_turn_blocks(lines, path), start=1):
        turn: Dict[str, object] = {}
        for field in TURN_SCALAR_FIELDS:
            turn[field] = _mapping_scalar(block, 4, field, path)
        for field in TURN_LIST_FIELDS:
            turn[field] = _mapping_list(block, 4, field, path)
        if not _literal_block(block, 4, "instruction", path).strip():
            raise ValueError(f"{path}: empty instruction in turn {number}")
        turns.append(turn)
    return SequenceManifest(
        path=f"{path.parent.parent.name}/{path.parent.name}",
        sequence_id=_mapping_scalar(lines, 0, "id", path) or "",
        lang=_mapping_scalar(lines, 0, "language", path) or "",
        repo=_mapping_scalar(meta, 2, "repo", path) or "",
        verified=_mapping_scalar(meta, 2, "verified", path, required=False),
        turns=tuple(turns),
    )


def _markdown_row(line: str, source: str) -> List[str]:
    if not (line.startswith("|") and line.endswith("|")):
        raise ValueError(f"{source}: malformed Markdown row: {line}")
    return [cell.strip() for cell in line[1:-1].split("|")]


def _parse_table(
    block: str, first_header: str, source: str
) -> Tuple[List[str], Dict[str, List[str]]]:
    lines = block.splitlines()
    candidates = []
    for index, line in enumerate(lines):
        if line.startswith("|") and _markdown_row(line, source)[0] == first_header:
            candidates.append(index)
    if len(candidates) != 1:
        raise ValueError(f"{source}: expected exactly one '{first_header}' table")
    header_index = candidates[0]
    headers = _markdown_row(lines[header_index], source)
    if len(lines) <= header_index + 1:
        raise ValueError(f"{source}: table has no divider")
    divider = _markdown_row(lines[header_index + 1], source)
    invalid_divider = any(not re.fullmatch(r":?-{3,}:?", cell) for cell in divider)
    if len(divider) != len(headers) or invalid_divider:
        raise ValueError(f"{source}: invalid table divider")

    rows: Dict[str, List[str]] = {}
    for line in lines[header_index + 2 :]:
        if not line.startswith("|"):
            break
        cells = _markdown_row(line, source)
        if len(cells) != len(headers):
            raise ValueError(
                f"{source}: row has {len(cells)} cells, expected {len(headers)}: {line}"
            )
        if cells[0] in rows:
            raise ValueError(f"{source}: duplicate row {cells[0]}")
        rows[cells[0]] = cells[1:]
    if not rows:
        raise ValueError(f"{source}: table has no data rows")
    return headers[1:], rows


def _marked_block(text: str, marker: str) -> str:
    begin = re.search(rf"<!-- {re.escape(marker)}:BEGIN[^>]*-->", text)
    end = re.search(rf"<!-- {re.escape(marker)}:END -->", text)
    if begin is None or end is None or begin.end() >= end.start():
        raise ValueError(f"{BENCHMARK_PATH}: missing or invalid {marker} block")
    return text[begin.end() : end.start()]


def _archived_block(text: str) -> str:
    heading = "### Archived — deepseek-v4-flash"
    start = text.find(heading)
    if start < 0:
        raise ValueError(f"{BENCHMARK_PATH}: missing '{heading}' table")
    end = text.find("\n## ", start + len(heading))
    if end < 0:
        raise ValueError(f"{BENCHMARK_PATH}: archived table has no following section")
    return text[start:end]


def _quantity(value: str) -> int:
    match = QUANTITY_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid quantity: {value}")
    factor = {"": 1, "K": 1_000, "M": 1_000_000}[match.group("suffix")]
    return round(float(match.group("number")) * factor)


def _parse_oneshot_cell(cell: str, location: str) -> Optional[OneShotCell]:
    if cell == "-":
        return None
    if cell in {"PASS", "FAIL", "INFRA", "LEAK", "FAIL+LEAK", "INFRA+LEAK"}:
        return OneShotCell(cell, cell, None, None, None, None, None, None, None, None)
    match = ONESHOT_CELL_RE.fullmatch(cell)
    if match is None:
        raise ValueError(f"{location}: cannot parse cell: {cell}")
    try:
        judge = None if match.group("judge") == "?" else float(match.group("judge"))
        cost = None if match.group("cost") == "?" else float(match.group("cost"))
        steps_value = int(match.group("steps"))
        return OneShotCell(
            raw=cell,
            verdict=match.group("verdict"),
            judge=judge,
            cost=cost,
            minutes=float(match.group("minutes")),
            steps=None if steps_value == 1 else steps_value,
            input_tokens=_quantity(match.group("input")),
            output_tokens=_quantity(match.group("output")),
            reasoning_tokens=_quantity(match.group("reasoning")),
            cache_read=_quantity(match.group("cache")),
        )
    except ValueError as exc:
        raise ValueError(f"{location}: cannot parse cell: {cell}") from exc


def _parse_sequence_cell(cell: str, location: str) -> Optional[SequenceCell]:
    if cell == "—":
        return None
    match = SEQUENCE_CELL_RE.fullmatch(cell)
    if match is None:
        raise ValueError(f"{location}: cannot parse cell: {cell}")
    try:
        return SequenceCell(
            raw=cell,
            passed=int(match.group("passed")),
            turns=int(match.group("turns")),
            score=float(match.group("score")),
            cost=float(match.group("cost")),
            tokens=_quantity(match.group("tokens")),
            minutes=float(match.group("minutes")),
        )
    except ValueError as exc:
        raise ValueError(f"{location}: cannot parse cell: {cell}") from exc


def _geomean(values: Iterable[float]) -> Optional[float]:
    usable = [value for value in values if value > 0]
    if not usable:
        return None
    return math.exp(sum(math.log(value) for value in usable) / len(usable))


def _positive_median(values: Iterable[Optional[float]]) -> Optional[float]:
    usable = [value for value in values if value is not None and value > 0]
    return statistics.median(usable) if usable else None


def _rounded_map(values: Dict[str, float]) -> str:
    rounded = {key: round(value, 6) for key, value in values.items()}
    return json.dumps(rounded, separators=(",", ":"))


def _json_list(values: Iterable[object]) -> str:
    return json.dumps(list(values), separators=(",", ":"))


def _display(value: object, digits: int = 3) -> str:
    if value is None or value == "":
        return UNKNOWN
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _metric_indexes(
    cells: Dict[str, OneShotCell],
    medians: Dict[str, Dict[str, float]],
    metric: str,
) -> Tuple[Optional[float], Dict[str, float], int]:
    ratios = {}
    excluded = 0
    for column, cell in cells.items():
        value = getattr(cell, metric)
        median = medians[column].get(metric)
        if value is None or value <= 0 or median is None or median <= 0:
            excluded += 1
            continue
        ratios[column] = value / median
    return _geomean(ratios.values()), ratios, excluded


def _sequence_indexes(
    cells: Dict[str, SequenceCell],
    medians: Dict[str, Dict[str, float]],
    metric: str,
) -> Tuple[Optional[float], Dict[str, float], int]:
    ratios = {}
    excluded = 0
    for column, cell in cells.items():
        value = getattr(cell, metric)
        median = medians[column].get(metric)
        if value <= 0 or median is None or median <= 0:
            excluded += 1
            continue
        ratios[column] = value / median
    return _geomean(ratios.values()), ratios, excluded


def _sequence_per_turn_indexes(
    cells: Dict[str, SequenceCell],
    medians: Dict[str, Dict[str, float]],
    metric: str,
) -> Tuple[Optional[float], Dict[str, float]]:
    median_key = f"{metric}_per_turn"
    ratios = {}
    for column, cell in cells.items():
        value = getattr(cell, metric) / cell.turns if cell.turns else 0
        median = medians[column].get(median_key)
        if value > 0 and median is not None and median > 0:
            ratios[column] = value / median
    return _geomean(ratios.values()), ratios


def _load_local_sequence_results(
    manifests: Sequence[SequenceManifest],
) -> Tuple[List[str], Dict[str, Dict[str, SequenceCell]], int]:
    files = set(REPO_ROOT.glob("results-longrun*/**/results.json"))
    files.update(REPO_ROOT.glob("results-longrun*/**/results.corrected.json"))
    if not files:
        return [], {}, 0
    ordered_files = sorted(files, key=lambda path: (str(path.parent), path.name != "results.json"))
    by_id = {manifest.sequence_id: manifest.path for manifest in manifests}
    columns: List[str] = []
    rows: Dict[str, Dict[str, SequenceCell]] = {}
    loaded = 0
    for path in ordered_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"{path}: invalid long-run results JSON") from exc
        results = data.get("results")
        if not isinstance(results, list):
            raise ValueError(f"{path}: results must be a list")
        for record in results:
            if not isinstance(record, dict) or record.get("sequence_id") not in by_id:
                continue
            turns = record.get("turns")
            aggregate = record.get("aggregate")
            if not isinstance(turns, list) or not turns or not isinstance(aggregate, dict):
                continue
            model = record.get("benchmark_model")
            provider = record.get("provider")
            if not isinstance(model, str) or not isinstance(provider, str):
                raise ValueError(f"{path}: long-run result lacks model/provider")
            column = f"{model}-{provider}"
            if column not in columns:
                columns.append(column)
            try:
                elapsed_values = [turn["provider"]["elapsed_ms"] for turn in turns]
                if any(value is None for value in elapsed_values):
                    continue
                passed = int(aggregate["passed"])
                total_turns = int(aggregate["total_turns"])
                score = float(aggregate["sum_final_score"])
                cost = float(aggregate["total_cost_usd"])
                tokens = int(aggregate["total_tokens"])
                minutes = sum(float(value) for value in elapsed_values) / 60_000
            except (KeyError, TypeError, ValueError) as exc:
                sequence_id = record.get("sequence_id")
                raise ValueError(
                    f"{path}: malformed long-run result for {sequence_id}"
                ) from exc
            raw = f"{passed}/{total_turns} Σ{score:.1f} ${cost:.2f} {tokens} {minutes:.3f}m"
            rows.setdefault(by_id[record["sequence_id"]], {})[column] = SequenceCell(
                raw=raw,
                passed=passed,
                turns=total_turns,
                score=score,
                cost=cost,
                tokens=tokens,
                minutes=minutes,
            )
            loaded += 1
    return columns, rows, loaded


def _format_map(values: Dict[str, object], digits: int = 3) -> str:
    if not values:
        return UNKNOWN
    parts = []
    for key, value in values.items():
        parts.append(f"{key}={_display(value, digits)}")
    return "<br>".join(parts)


def _markdown_cell(value: object) -> str:
    return _display(value).replace("|", "\\|").replace("\n", "<br>")


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_markdown_cell(value) for value in row) + " |")
    return "\n".join(lines)


def _sort_key(row: Dict[str, object]) -> Tuple[bool, float, bool, float, str]:
    pass_rate = row.get("pass_rate")
    effort = row.get("effort_index")
    return (
        pass_rate is None,
        float(pass_rate) if pass_rate is not None else math.inf,
        effort is None,
        -float(effort) if effort is not None else math.inf,
        str(row["path"]),
    )


def _turn_values(manifest: SequenceManifest, field: str) -> List[object]:
    values = []
    for turn in manifest.turns:
        value = turn[field]
        values.append(list(value) if isinstance(value, tuple) else value)
    return values


def main() -> None:
    oneshot_manifests = [
        _parse_oneshot_manifest(path) for path in sorted(ONESHOT_ROOT.rglob("case.yaml"))
    ]
    sequence_manifests = [
        _parse_sequence_manifest(path) for path in sorted(LONGRUN_ROOT.rglob("sequence.yaml"))
    ]

    benchmark = BENCHMARK_PATH.read_text(encoding="utf-8")
    main_columns, main_raw = _parse_table(
        _marked_block(benchmark, "RESULTS"), "case path", "RESULTS block"
    )
    archived_columns, archived_raw = _parse_table(
        _archived_block(benchmark), "case path", "Archived — deepseek-v4-flash"
    )
    sequence_columns, sequence_raw = _parse_table(
        _marked_block(benchmark, "LONGRUN-RESULTS"),
        "sequence (turns)",
        "LONGRUN-RESULTS block",
    )
    if len(set(main_columns + archived_columns)) != len(main_columns + archived_columns):
        raise ValueError("one-shot result tables contain duplicate model-client columns")

    manifest_by_path = {manifest.path: manifest for manifest in oneshot_manifests}
    sequence_by_path = {manifest.path: manifest for manifest in sequence_manifests}
    unknown_cases = (set(main_raw) | set(archived_raw)) - set(manifest_by_path)
    if unknown_cases:
        raise ValueError(f"BENCHMARK.md lists unknown one-shot cases: {sorted(unknown_cases)}")

    parsed_main: Dict[str, Dict[str, OneShotCell]] = {}
    parsed_archived: Dict[str, Dict[str, OneShotCell]] = {}
    for table_name, columns, raw_rows, destination in (
        ("RESULTS", main_columns, main_raw, parsed_main),
        ("Archived — deepseek-v4-flash", archived_columns, archived_raw, parsed_archived),
    ):
        for case_path, cells in raw_rows.items():
            destination[case_path] = {}
            for column, cell in zip(columns, cells):
                parsed = _parse_oneshot_cell(cell, f"{table_name} [{case_path}] [{column}]")
                if parsed is not None:
                    destination[case_path][column] = parsed

    parsed_sequences: Dict[str, Dict[str, SequenceCell]] = {}
    for label, cells in sequence_raw.items():
        match = re.fullmatch(r"(.+) \((\d+)\)", label)
        if match is None:
            raise ValueError(f"LONGRUN-RESULTS: invalid sequence label: {label}")
        sequence_path, turns_text = match.groups()
        if sequence_path not in sequence_by_path:
            raise ValueError(f"BENCHMARK.md lists unknown sequence: {sequence_path}")
        turns = int(turns_text)
        if turns != len(sequence_by_path[sequence_path].turns):
            manifest_turns = len(sequence_by_path[sequence_path].turns)
            raise ValueError(
                f"LONGRUN-RESULTS [{label}]: manifest has {manifest_turns} turns"
            )
        parsed_sequences[sequence_path] = {}
        for column, cell in zip(sequence_columns, cells):
            parsed = _parse_sequence_cell(cell, f"LONGRUN-RESULTS [{label}] [{column}]")
            if parsed is None:
                continue
            if parsed.turns != turns:
                raise ValueError(
                    f"LONGRUN-RESULTS [{label}] [{column}]: cell has {parsed.turns} turns"
                )
            parsed_sequences[sequence_path][column] = parsed

    local_columns, local_rows, local_record_count = _load_local_sequence_results(
        sequence_manifests
    )
    for sequence_path, columns in local_rows.items():
        parsed_sequences.setdefault(sequence_path, {}).update(columns)
    all_sequence_columns = list(sequence_columns)
    for column in local_columns:
        if column not in all_sequence_columns:
            all_sequence_columns.append(column)

    oneshot_columns = main_columns + archived_columns
    all_result_columns = list(oneshot_columns)
    for column in all_sequence_columns:
        if column not in all_result_columns:
            all_result_columns.append(column)

    oneshot_cells: Dict[str, Dict[str, OneShotCell]] = {}
    for manifest in oneshot_manifests:
        combined = {}
        combined.update(parsed_main.get(manifest.path, {}))
        combined.update(parsed_archived.get(manifest.path, {}))
        oneshot_cells[manifest.path] = combined

    oneshot_medians: Dict[str, Dict[str, float]] = {}
    for column in oneshot_columns:
        column_cells = [
            cells[column] for cells in oneshot_cells.values() if column in cells
        ]
        metric_medians = {}
        for metric in ("cost", "minutes", "total_tokens", "steps"):
            median = _positive_median(getattr(cell, metric) for cell in column_cells)
            if median is not None:
                metric_medians[metric] = median
        oneshot_medians[column] = metric_medians

    sequence_medians: Dict[str, Dict[str, float]] = {}
    for column in all_sequence_columns:
        column_cells = [
            cells[column] for cells in parsed_sequences.values() if column in cells
        ]
        metric_medians = {}
        for metric in ("minutes", "tokens"):
            median = _positive_median(getattr(cell, metric) for cell in column_cells)
            per_turn_median = _positive_median(
                getattr(cell, metric) / cell.turns if cell.turns else None
                for cell in column_cells
            )
            if median is not None:
                metric_medians[metric] = median
            if per_turn_median is not None:
                metric_medians[f"{metric}_per_turn"] = per_turn_median
        sequence_medians[column] = metric_medians

    rows: List[Dict[str, object]] = []
    oneshot_rows: List[Dict[str, object]] = []
    for manifest in oneshot_manifests:
        cells = oneshot_cells[manifest.path]
        cost_index, cost_by_column, cost_excluded = _metric_indexes(
            cells, oneshot_medians, "cost"
        )
        minutes_index, minutes_by_column, minutes_excluded = _metric_indexes(
            cells, oneshot_medians, "minutes"
        )
        tokens_index, tokens_by_column, tokens_excluded = _metric_indexes(
            cells, oneshot_medians, "total_tokens"
        )
        steps_index, steps_by_column, steps_excluded = _metric_indexes(
            cells, oneshot_medians, "steps"
        )
        n_infra = sum("INFRA" in cell.verdict for cell in cells.values())
        n_leak = sum("LEAK" in cell.verdict for cell in cells.values())
        eligible = [
            cell
            for cell in cells.values()
            if "INFRA" not in cell.verdict and "LEAK" not in cell.verdict
        ]
        n_pass = sum(cell.verdict == "PASS" for cell in eligible)
        n_fail = len(eligible) - n_pass
        pass_rate = n_pass / len(eligible) if eligible else None
        failed_columns = [
            column for column in oneshot_columns
            if column in cells and cells[column].verdict.startswith("FAIL")
        ]
        row: Dict[str, object] = {
            "record_type": "oneshot",
            "path": manifest.path,
            "id": manifest.case_id,
            "lang": manifest.lang,
            "repo": manifest.repo,
            "turns": None,
            "difficulty": manifest.difficulty,
            "task_type": manifest.task_type,
            "failure_modes": _json_list(manifest.failure_modes),
            "prompt_style": manifest.prompt_style,
            "spec_level": manifest.spec_level,
            "test_visibility": manifest.test_visibility,
            "capability_tags": _json_list(manifest.capability_tags),
            "verified": manifest.verified,
            "merged_at": manifest.merged_at,
            "instruction_words": manifest.instruction_words,
            "n_cols_run": len(cells),
            "n_pass": n_pass,
            "n_fail": n_fail,
            "n_infra": n_infra,
            "n_leak": n_leak,
            "pass_rate": pass_rate,
            "failed_columns": _json_list(failed_columns),
            "cost_index": cost_index,
            "minutes_index": minutes_index,
            "tokens_index": tokens_index,
            "steps_index": steps_index,
            "effort_index": _geomean(
                value for value in (cost_index, minutes_index, tokens_index)
                if value is not None
            ),
            "cost_excluded": cost_excluded,
            "minutes_excluded": minutes_excluded,
            "tokens_excluded": tokens_excluded,
            "steps_excluded": steps_excluded,
            "median_minutes": _positive_median(cell.minutes for cell in cells.values()),
            "median_total_tokens": _positive_median(
                cell.total_tokens for cell in cells.values()
            ),
            "median_steps": _positive_median(cell.steps for cell in cells.values()),
            "minutes_per_turn_index": None,
            "tokens_per_turn_index": None,
            "cost_index_by_column": _rounded_map(cost_by_column),
            "minutes_index_by_column": _rounded_map(minutes_by_column),
            "tokens_index_by_column": _rounded_map(tokens_by_column),
            "steps_index_by_column": _rounded_map(steps_by_column),
            "passes_by_column": UNKNOWN,
            "minutes_per_turn_index_by_column": UNKNOWN,
            "tokens_per_turn_index_by_column": UNKNOWN,
        }
        for column in all_result_columns:
            row[column] = cells[column].raw if column in cells else None
        rows.append(row)
        oneshot_rows.append(row)

    sequence_rows: List[Dict[str, object]] = []
    for manifest in sequence_manifests:
        cells = parsed_sequences.get(manifest.path, {})
        minutes_index, minutes_by_column, minutes_excluded = _sequence_indexes(
            cells, sequence_medians, "minutes"
        )
        tokens_index, tokens_by_column, tokens_excluded = _sequence_indexes(
            cells, sequence_medians, "tokens"
        )
        minutes_per_turn_index, minutes_per_turn_by_column = _sequence_per_turn_indexes(
            cells, sequence_medians, "minutes"
        )
        tokens_per_turn_index, tokens_per_turn_by_column = _sequence_per_turn_indexes(
            cells, sequence_medians, "tokens"
        )
        pass_rates = [cell.passed / cell.turns for cell in cells.values() if cell.turns]
        passed_by_column = {
            column: f"{cells[column].passed}/{cells[column].turns}"
            for column in all_sequence_columns
            if column in cells
        }
        failed_columns = [
            column for column in all_sequence_columns
            if column in cells and cells[column].passed < cells[column].turns
        ]
        row = {
            "record_type": "sequence",
            "path": manifest.path,
            "id": manifest.sequence_id,
            "lang": manifest.lang,
            "repo": manifest.repo,
            "turns": len(manifest.turns),
            "difficulty": _json_list(_turn_values(manifest, "difficulty")),
            "task_type": _json_list(_turn_values(manifest, "task_type")),
            "failure_modes": _json_list(_turn_values(manifest, "failure_modes")),
            "prompt_style": _json_list(_turn_values(manifest, "prompt_style")),
            "spec_level": _json_list(_turn_values(manifest, "spec_level")),
            "test_visibility": _json_list(_turn_values(manifest, "test_visibility")),
            "capability_tags": _json_list(_turn_values(manifest, "capability_tags")),
            "verified": manifest.verified,
            "merged_at": None,
            "instruction_words": None,
            "n_cols_run": len(cells),
            "n_pass": sum(cell.passed for cell in cells.values()),
            "n_fail": sum(cell.turns - cell.passed for cell in cells.values()),
            "n_infra": 0,
            "n_leak": 0,
            "pass_rate": statistics.mean(pass_rates) if pass_rates else None,
            "failed_columns": _json_list(failed_columns),
            "cost_index": None,
            "minutes_index": minutes_index,
            "tokens_index": tokens_index,
            "steps_index": None,
            "effort_index": _geomean(
                value for value in (minutes_per_turn_index, tokens_per_turn_index)
                if value is not None
            ),
            "cost_excluded": None,
            "minutes_excluded": minutes_excluded,
            "tokens_excluded": tokens_excluded,
            "steps_excluded": None,
            "median_minutes": _positive_median(cell.minutes for cell in cells.values()),
            "median_total_tokens": _positive_median(cell.tokens for cell in cells.values()),
            "median_steps": None,
            "minutes_per_turn_index": minutes_per_turn_index,
            "tokens_per_turn_index": tokens_per_turn_index,
            "cost_index_by_column": UNKNOWN,
            "minutes_index_by_column": _rounded_map(minutes_by_column),
            "tokens_index_by_column": _rounded_map(tokens_by_column),
            "steps_index_by_column": UNKNOWN,
            "passes_by_column": json.dumps(passed_by_column, separators=(",", ":")),
            "minutes_per_turn_index_by_column": _rounded_map(
                minutes_per_turn_by_column
            ),
            "tokens_per_turn_index_by_column": _rounded_map(tokens_per_turn_by_column),
        }
        for column in all_result_columns:
            row[column] = cells[column].raw if column in cells else None
        rows.append(row)
        sequence_rows.append(row)

    base_fields = [
        "record_type",
        "path",
        "id",
        "lang",
        "repo",
        "turns",
        "difficulty",
        "task_type",
        "failure_modes",
        "prompt_style",
        "spec_level",
        "test_visibility",
        "capability_tags",
        "verified",
        "merged_at",
        "instruction_words",
        "n_cols_run",
        "n_pass",
        "n_fail",
        "n_infra",
        "n_leak",
        "pass_rate",
        "failed_columns",
        "cost_index",
        "minutes_index",
        "tokens_index",
        "steps_index",
        "effort_index",
        "cost_excluded",
        "minutes_excluded",
        "tokens_excluded",
        "steps_excluded",
        "median_minutes",
        "median_total_tokens",
        "median_steps",
        "minutes_per_turn_index",
        "tokens_per_turn_index",
        "cost_index_by_column",
        "minutes_index_by_column",
        "tokens_index_by_column",
        "steps_index_by_column",
        "passes_by_column",
        "minutes_per_turn_index_by_column",
        "tokens_per_turn_index_by_column",
    ]
    csv_fields = base_fields + all_result_columns
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_DIR / "inventory.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _display(row.get(field), 6) for field in csv_fields})

    sorted_oneshots = sorted(oneshot_rows, key=_sort_key)
    sorted_sequences = sorted(sequence_rows, key=_sort_key)
    oneshot_table_rows = []
    for row in sorted_oneshots:
        manifest = manifest_by_path[str(row["path"])]
        indexes = {
            "cost": row["cost_index"],
            "min": row["minutes_index"],
            "tok": row["tokens_index"],
            "steps": row["steps_index"],
        }
        medians = {
            "min": row["median_minutes"],
            "tok": row["median_total_tokens"],
            "steps": row["median_steps"],
        }
        exclusions = {
            "cost": row["cost_excluded"],
            "min": row["minutes_excluded"],
            "tok": row["tokens_excluded"],
            "steps": row["steps_excluded"],
        }
        oneshot_table_rows.append(
            [
                row["path"],
                row["id"],
                row["lang"],
                row["difficulty"],
                row["task_type"],
                ", ".join(manifest.failure_modes) or "[]",
                f"{row['prompt_style']} / {row['spec_level']} / {row['test_visibility']}",
                ", ".join(manifest.capability_tags),
                row["verified"],
                row["merged_at"],
                row["instruction_words"],
                f"{row['n_cols_run']}/{row['n_pass']}/{row['n_infra']}/{row['n_leak']}",
                row["pass_rate"],
                ", ".join(json.loads(str(row["failed_columns"]))) or "[]",
                _format_map(indexes),
                row["effort_index"],
                _format_map(exclusions, 0),
                _format_map(medians),
            ]
        )

    sequence_table_rows = []
    for row in sorted_sequences:
        manifest = sequence_by_path[str(row["path"])]
        total_indexes = {"min": row["minutes_index"], "tok": row["tokens_index"]}
        per_turn_indexes = {
            "min/turn": row["minutes_per_turn_index"],
            "tok/turn": row["tokens_per_turn_index"],
        }
        sequence_table_rows.append(
            [
                row["path"],
                row["id"],
                row["lang"],
                row["repo"],
                row["turns"],
                "<br>".join(str(value) for value in _turn_values(manifest, "difficulty")),
                "<br>".join(str(value) for value in _turn_values(manifest, "task_type")),
                "<br>".join(
                    ", ".join(value) if value else "[]"
                    for value in _turn_values(manifest, "failure_modes")
                ),
                "<br>".join(
                    f"{style} / {spec} / {visibility}"
                    for style, spec, visibility in zip(
                        _turn_values(manifest, "prompt_style"),
                        _turn_values(manifest, "spec_level"),
                        _turn_values(manifest, "test_visibility"),
                    )
                ),
                "<br>".join(
                    ", ".join(value)
                    for value in _turn_values(manifest, "capability_tags")
                ),
                row["n_cols_run"],
                _format_map(json.loads(str(row["passes_by_column"])), 0),
                row["pass_rate"],
                _format_map(total_indexes),
                _format_map(per_turn_indexes),
                row["effort_index"],
            ]
        )

    no_data = [row["path"] for row in rows if row["n_cols_run"] == 0]
    raw_note = (
        f"{local_record_count} local raw long-run record(s) overrode matching rounded cells."
        if local_record_count
        else "No local raw long-run results were present."
    )
    markdown = "\n".join(
        [
            "# GOLD candidate inventory",
            "",
            "Evidence only: this inventory ranks no candidates and selects nothing. "
            "UNKNOWN means evidence was absent, never zero. Historical model-client columns in "
            "the CSV use the exact BENCHMARK.md headers and retain each source cell. " + raw_note,
            "",
            "## Columns and formulas",
            "",
            "Common manifest columns are `path`, `id`, `lang`, `repo`, `turns`, and the "
            "classification fields. One-shot `words` is `len(instruction.split())`; sequence "
            "classification cells preserve turn order. `verified` and `merged_at` remain UNKNOWN "
            "when a manifest omits them.",
            "",
            "For one-shots, `run/pass/infra/leak` counts non-missing cells, PASS cells, INFRA "
            "cells, and LEAK cells. `pass_rate = PASS / (PASS + FAIL)`; INFRA and every LEAK "
            "variant are excluded. `failed` lists columns whose verdict contains FAIL. Total "
            "tokens are fresh input + output + reasoning + cache read. For each metric and "
            "model-client, the case value is divided by that column's median positive known "
            "value; `indexes` is the geometric mean of those ratios across columns. "
            "`effort = geomean(cost_index, minutes_index, tokens_index)`. A reported single "
            "step is UNKNOWN. Zero/UNKNOWN observations are omitted and counted in `excluded`. "
            "`medians` are the case's raw positive medians across model-client columns.",
            "",
            "For sequences, `passes` preserves each column's passed/turns value and `pass_rate` "
            "is the arithmetic mean of the per-column turn pass rates. `total indexes` divide "
            "tokens and minutes by each model-client's median sequence and geometrically average "
            "the ratios. `per-turn indexes` repeat that calculation after dividing every sequence "
            "by its turn count. `effort = geomean(minutes_per_turn_index, "
            "tokens_per_turn_index)`, so sequence length alone does not make work look harder. "
            "The CSV also contains every per-column ratio and exclusion count.",
            "",
            "Both tables are sorted by `pass_rate` ascending, then `effort` descending. Index "
            "1.0 is typical for the historical model-client columns that ran the item.",
            "",
            "## One-shots",
            "",
            _markdown_table(
                [
                    "case",
                    "id",
                    "lang",
                    "difficulty",
                    "task type",
                    "failure modes",
                    "prompt / spec / tests",
                    "capabilities",
                    "verified",
                    "merged",
                    "words",
                    "run/pass/infra/leak",
                    "pass_rate",
                    "failed",
                    "indexes",
                    "effort",
                    "excluded",
                    "medians",
                ],
                oneshot_table_rows,
            ),
            "",
            "## Long-run sequences",
            "",
            _markdown_table(
                [
                    "sequence",
                    "id",
                    "lang",
                    "repo",
                    "turns",
                    "difficulty by turn",
                    "task type by turn",
                    "failure modes by turn",
                    "prompt / spec / tests by turn",
                    "capabilities by turn",
                    "runs",
                    "passes",
                    "pass_rate",
                    "total indexes",
                    "per-turn indexes",
                    "effort",
                ],
                sequence_table_rows,
            ),
            "",
            "## Cases with no historical data",
            "",
            *(f"- {path}" for path in no_data),
            *( ["- None."] if not no_data else [] ),
            "",
        ]
    )
    (OUTPUT_DIR / "inventory.md").write_text(markdown, encoding="utf-8")

    benchmark_cells = (
        len(main_raw) * len(main_columns)
        + len(archived_raw) * len(archived_columns)
        + len(sequence_raw) * len(sequence_columns)
    )
    print(
        f"wrote {len(oneshot_rows)} one-shots and {len(sequence_rows)} sequences; "
        f"parsed {benchmark_cells} BENCHMARK.md data cells"
    )


if __name__ == "__main__":
    main()

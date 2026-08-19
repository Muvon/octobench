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
import statistics
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scoring.aggregate import compute_cost, normalize_token_counts  # noqa: E402


def load(pattern: str) -> dict:
    records = {}
    # A pattern may be several whitespace-separated globs; later globs (and later
    # paths within a glob) win, so reruns can be layered over the base run.
    paths = [p for g in pattern.split() for p in sorted(glob.glob(g))]
    for path in paths:
        try:
            data = json.loads(open(path).read())
        except Exception:
            continue
        for r in data.get("results", []):
            r["_result_path"] = path
            records[r["case_id"]] = r
    return records


def _count_steps(record: dict) -> int:
    """Count agent steps from the provider trace (tool_use events + 1 for final message)."""
    result_path = Path(record.get("_result_path", ""))
    cid = record["case_id"]
    traces = list(result_path.parent.glob(f"{cid}/*/logs/provider.raw.jsonl"))
    if not traces:
        return 0
    steps = 0
    for line in traces[0].read_text(errors="replace").splitlines():
        try:
            obj = json.loads(line)
            if obj.get("type") == "tool_use":
                steps += 1
            elif record.get("provider") == "codex" and obj.get("type") == "item.started":
                # Codex JSONL represents tool activity as typed items rather
                # than generic tool_use events. Count each started action once;
                # item.completed and item.updated are lifecycle events for the
                # same action and must not inflate the total.
                item_type = (obj.get("item") or {}).get("type")
                if item_type in {
                    "command_execution",
                    "file_change",
                    "mcp_tool_call",
                    "web_search",
                    "todo_list",
                }:
                    steps += 1
        except Exception:
            pass
    return steps + 1  # +1 for the final assistant message


def _fmt_tok(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    return f"{n / 1000:.0f}K"


def _report_cost(record: dict, pricing_by_model: dict[str, dict]) -> float:
    # Claude's provider-reported bill includes cache-write premiums that the
    # flat model table cannot reproduce. Other stored costs are derived values,
    # so refresh them from canonical tokens and the current price table.
    if record.get("provider") == "claude":
        return float(record.get("cost_usd") or 0)
    model = record.get("model") or record.get("benchmark_model")
    pricing = pricing_by_model.get(str(model), {})
    if not pricing:
        return float(record.get("cost_usd") or 0)
    fresh, cache, output, reasoning = normalize_token_counts(record.get("tokens", {}))
    return float(compute_cost(fresh, cache, output, pricing, reasoning) or 0)


def cell(r: dict | None) -> str:
    if r is None:
        return "-"
    leaked = bool(r.get("_integrity_violations"))
    if r.get("infra_failed"):
        return "INFRA+LEAK" if leaked else "INFRA"
    s = r.get("scoring", {})
    if leaked:
        val = "FAIL+LEAK" if s.get("validation_failed") else "LEAK"
    else:
        val = "FAIL" if s.get("validation_failed") else "PASS"
    judge = r.get("judge", {}).get("score")
    cost = r.get("_report_cost_usd", r.get("cost_usd"))
    mins = r.get("result", {}).get("elapsed_ms", 0) / 60000
    cost_s = f"${cost:.2f}" if cost is not None else "$?"
    steps = _count_steps(r)
    tok_in, tok_cache, tok_out, tok_reas = normalize_token_counts(r.get("tokens", {}))
    tok_total = tok_in + tok_out + tok_reas
    tok_s = (
        f"{_fmt_tok(tok_total)} tok "
        f"({_fmt_tok(tok_in)}/{_fmt_tok(tok_out)}/{_fmt_tok(tok_reas)})"
    )
    cache_s = f"{_fmt_tok(tok_cache)} cache"
    return (
        f"{val} j={judge if judge is not None else '?'} {cost_s} {mins:.0f}m "
        f"· {steps} steps · {tok_s} · {cache_s}"
    )


def totals(records: dict, order: list) -> str:
    done = [records[c] for c in order if c in records]
    if not done:
        return "pending"
    ok = sum(1 for r in done if not (r["scoring"].get("validation_failed")
                                     or r.get("infra_failed")
                                     or r.get("_integrity_violations")))
    # An infra-failed record also carries validation_failed in some providers;
    # counting it in both columns rendered six failures as "7 FAIL · 1 INFRA".
    fail = sum(1 for r in done if r["scoring"].get("validation_failed")
              and not r.get("_integrity_violations")
              and not r.get("infra_failed"))
    leak = sum(1 for r in done if r.get("_integrity_violations"))
    infra = sum(1 for r in done if r.get("infra_failed"))
    count = len(done)
    j = sum(r.get("judge", {}).get("score") or 0 for r in done)
    cost = sum(r.get("_report_cost_usd", r.get("cost_usd")) or 0 for r in done)
    hours = sum(r.get("result", {}).get("elapsed_ms", 0) for r in done) / 3600000
    normalized = [normalize_token_counts(r.get("tokens", {})) for r in done]
    tok_in = sum(t[0] for t in normalized)
    cache = sum(t[1] for t in normalized)
    tok_out = sum(t[2] for t in normalized)
    tok_reas = sum(t[3] for t in normalized)
    fresh_total = tok_in + tok_out + tok_reas
    parts = [f"**{ok}/{count}** PASS ({ok / count * 100:.1f}%)"]
    if fail:
        parts.append(f"{fail} FAIL")
    if leak:
        parts.append(f"{leak} LEAK")
    if infra:
        parts.append(f"{infra} INFRA")
    # Per-case central tendency is reported as a MEDIAN, not a mean: one pathological
    # case (a client burning hours on a task it never solves) moves the mean of 50 by
    # minutes per case and says nothing about the other 49. Max is kept beside it so
    # that tail stays visible instead of being smoothed away.
    case_mins = sorted(r.get("result", {}).get("elapsed_ms", 0) / 60000 for r in done)
    case_costs = [r.get("_report_cost_usd", r.get("cost_usd")) or 0 for r in done]
    parts.append(f"jAvg {j / count:.2f}")
    parts.append(
        f"${cost:.2f} total (${statistics.median(case_costs):.3f}/case median)"
    )
    parts.append(
        f"{hours:.1f}h agent ({statistics.median(case_mins):.1f}m/case median, "
        f"max {case_mins[-1]:.0f}m)"
    )
    med_fresh = statistics.median(t[0] + t[2] + t[3] for t in normalized)
    parts.append(
        f"{_fmt_tok(fresh_total)} tok ({_fmt_tok(round(med_fresh))}/case median; "
        f"{_fmt_tok(tok_in)} in / {_fmt_tok(tok_out)} out / {_fmt_tok(tok_reas)} reas"
        f")"
    )
    parts.append(
        f"{_fmt_tok(cache)} cache read "
        f"({_fmt_tok(round(statistics.median(t[1] for t in normalized)))}/case median)"
    )
    return " · ".join(parts)


def discover_cases(repo_root: Path) -> dict[str, dict]:
    """Map stable result IDs to current paths and provenance metadata."""
    cases = {}
    cases_root = repo_root / "cases"
    for case_file in cases_root.rglob("case.yaml"):
        rel = case_file.relative_to(cases_root).as_posix()
        if "oneshot" not in rel:
            continue
        try:
            case = yaml.safe_load(case_file.read_text())
            case_id = case.get("id")
        except Exception:
            continue
        if case_id:
            cases[case_id] = {
                "path": case_file.parent.relative_to(cases_root).as_posix(),
                "meta": case.get("meta", {}),
            }
    return cases


def _provider_actions(trace: Path, provider: str) -> list[tuple[str, bool]]:
    """Extract tool inputs only, excluding URLs echoed in tool results/source."""
    actions = []
    for line in trace.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except Exception:
            continue
        action = None
        network = False
        if provider == "codex" and event.get("type") == "item.started":
            item = event.get("item", {})
            if item.get("type") == "command_execution":
                action = item.get("command")
                network = bool(re.search(
                    r"\b(?:git\s+(?:fetch|clone|pull|ls-remote)|curl|wget|ssh|scp|rsync)\b",
                    action,
                    re.IGNORECASE,
                ))
        elif provider == "octomind" and event.get("type") == "tool_use":
            tool = event.get("tool")
            params = event.get("params") or {}
            action = json.dumps({
                "tool": tool,
                "params": params,
            })
            network = (
                tool == "knowledge" and bool(params.get("source"))
            ) or (
                tool == "shell" and bool(re.search(
                    r"\b(?:git\s+(?:fetch|clone|pull|ls-remote)|curl|wget|ssh|scp|rsync)\b",
                    str(params.get("command", "")), re.IGNORECASE,
                ))
            )
        elif provider == "opencode" and event.get("type") == "tool_use":
            part = event.get("part", {})
            tool = part.get("tool")
            inputs = part.get("state", {}).get("input") or {}
            action = json.dumps({
                "tool": tool,
                "input": inputs,
            })
            network = tool in {"webfetch", "websearch"} or (
                tool == "bash" and bool(re.search(
                    r"\b(?:git\s+(?:fetch|clone|pull|ls-remote)|curl|wget|ssh|scp|rsync)\b",
                    str(inputs.get("command", "")), re.IGNORECASE,
                ))
            )
        if action:
            actions.append((action, network))
    return actions


def audit_integrity(record: dict, case: dict | None) -> list[str]:
    """Detect provider access to hidden assets or the case's upstream solution."""
    if not case:
        return []
    result_path = Path(record.get("_result_path", ""))
    traces = list(result_path.parent.glob(
        f"{record['case_id']}/*/logs/provider.raw.jsonl"
    ))
    if not traces:
        return []

    meta = case.get("meta", {})
    repo = str(meta.get("repo", "")).rstrip("/")
    repo_match = re.search(r"github\.com/([^/]+/[^/]+)$", repo, re.IGNORECASE)
    slug = repo_match.group(1).removesuffix(".git") if repo_match else ""
    pr = str(meta.get("pr", ""))
    gold = str(meta.get("gold_sha", ""))
    violations = set()

    search_re = re.compile(
        r"\b(?:websearch|web_search|search_query)\b|"
        r"https?://(?:www\.)?(?:google|bing|duckduckgo)\.|"
        r"https?://(?:search\.brave|grep\.app|sourcegraph\.com)",
        re.IGNORECASE,
    )

    hidden_re = re.compile(
        r"(?<![A-Za-z0-9_.-])/(?:case|cases)(?:/|\b)|\$CASE_DIR|\bCASE_DIR=",
        re.IGNORECASE,
    )
    if slug:
        same_repo_re = re.compile(
            rf"https?://(?:raw\.githubusercontent\.com/{re.escape(slug)}/"
            rf"|(?:www\.)?github\.com/{re.escape(slug)}(?:\.git)?(?:/|\b))",
            re.IGNORECASE,
        )
        current_source_re = re.compile(
            rf"raw\.githubusercontent\.com/{re.escape(slug)}/",
            re.IGNORECASE,
        )
        repo_network_re = re.compile(
            rf"\b(?:git\s+(?:fetch|clone|ls-remote)|curl|wget)\b[^\n]*"
            rf"(?:github\.com/{re.escape(slug)}|raw\.githubusercontent\.com/{re.escape(slug)})",
            re.IGNORECASE,
        )
        pr_re = re.compile(
            rf"github\.com/{re.escape(slug)}/(?:pull|issues)/{re.escape(pr)}(?:\D|$)",
            re.IGNORECASE,
        ) if pr else None
        gold_re = re.compile(re.escape(gold), re.IGNORECASE) if gold else None

    provider = str(record.get("provider", ""))
    for trace in traces:
        for action, network in _provider_actions(trace, provider):
            if hidden_re.search(action):
                violations.add("hidden case assets")
            if network and search_re.search(action):
                violations.add("web search")
            if not network or not slug or not same_repo_re.search(action):
                continue
            if current_source_re.search(action) or repo_network_re.search(action):
                violations.add("current upstream source")
            if pr_re and pr_re.search(action):
                violations.add("exact upstream PR")
            if gold_re and gold_re.search(action):
                violations.add("gold commit")
            # Reading another PR from the same repository can expose a follow-up
            # or superseding version of the fix (observed in the CakePHP case).
            if re.search(
                rf"github\.com/{re.escape(slug)}/pull/\d+", action, re.IGNORECASE
            ):
                violations.add("upstream PR")
    return sorted(violations)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    cases = discover_cases(repo_root)
    model_specs = yaml.safe_load((repo_root / "configs/models.yaml").read_text())["models"]
    pricing_by_model = {
        name: spec.get("pricing") or {} for name, spec in model_specs.items()
    }
    providers = []
    for arg in sys.argv[1:]:
        label, pattern = arg.split("=", 1)
        records = load(pattern)
        for case_id, record in records.items():
            record["_report_cost_usd"] = _report_cost(record, pricing_by_model)
            record["_integrity_violations"] = audit_integrity(
                record, cases.get(case_id)
            )
        providers.append((label, records))

    # Include ALL discovered oneshot cases (not just those with results) so
    # empty rows appear for cases that haven't been run yet.
    order = sorted(
        cases.keys(),
        key=lambda c: cases.get(c, {}).get("path", c),
    )

    lines = []
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"_Updated {stamp}. val = hidden gold tests; j = judge 0-100; "
                 f"cost; agent runtime (excludes setup, validation, and judging). "
                 f"Roll-ups below the table report per-case MEDIANS, not means. "
                 f"LEAK = upstream solution access, excluded from passes._\n")
    header = "| case path | " + " | ".join(label for label, _ in providers) + " |"
    lines.append(header)
    lines.append("|---" * (len(providers) + 1) + "|")
    for cid in order:
        row = " | ".join(cell(recs.get(cid)) for _, recs in providers)
        lines.append(f"| {cases.get(cid, {}).get('path', cid)} | {row} |")
    lines.append("")
    for label, recs in providers:
        lines.append(f"- **{label}**: {totals(recs, order)}")
    section = "\n".join(lines)

    # --- Summary block: model × harness matrix ---
    # Parse labels as "{model}-{harness}" (split on last "-").
    summary: dict[str, dict[str, dict]] = {}
    for label, recs in providers:
        parts = label.rsplit("-", 1)
        model, harness = (parts[0], parts[1]) if len(parts) == 2 else (label, "result")
        summary.setdefault(model, {})[harness] = recs
    all_harnesses = sorted({h for m in summary.values() for h in m})

    summary_lines = [
        "_Cross-model × harness matrix. Each cell = pass-rate · judge average · "
        "total cost and median per case · agent runtime (median per case, plus the "
        "slowest single case) · non-cache tokens. Per-case figures are medians: one "
        "runaway case distorts a 50-case mean and tells you nothing about the other 49._\n",
        "| model | " + " | ".join(all_harnesses) + " |",
        "|---" * (len(all_harnesses) + 1) + "|",
    ]
    for model in sorted(summary):
        cells = []
        for harness in all_harnesses:
            recs = summary[model].get(harness)
            cells.append(totals(recs, order) if recs else "-")
        summary_lines.append(f"| {model} | " + " | ".join(cells) + " |")
    summary_section = "\n".join(summary_lines)

    bench = repo_root / "BENCHMARK.md"
    text = bench.read_text()
    new = re.sub(
        r"(<!-- RESULTS:BEGIN[^>]*-->\n).*?(<!-- RESULTS:END -->)",
        lambda m: m.group(1) + section + "\n" + m.group(2),
        text,
        flags=re.DOTALL,
    )
    new = re.sub(
        r"(<!-- SUMMARY:BEGIN[^>]*-->\n).*?(<!-- SUMMARY:END -->)",
        lambda m: m.group(1) + summary_section + "\n" + m.group(2),
        new,
        flags=re.DOTALL,
    )
    bench.write_text(new)
    print(f"BENCHMARK.md updated ({len(order)} cases, {len(providers)} providers, "
          f"{len(summary)} models × {len(all_harnesses)} harnesses)")


if __name__ == "__main__":
    main()

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
            r["_result_path"] = path
            records[r["case_id"]] = r
    return records


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
    cost = r.get("cost_usd")
    mins = r.get("result", {}).get("elapsed_ms", 0) / 60000
    cost_s = f"${cost:.2f}" if cost is not None else "$?"
    return f"{val} j={judge if judge is not None else '?'} {cost_s} {mins:.0f}m"


def totals(records: dict, order: list) -> str:
    done = [records[c] for c in order if c in records]
    if not done:
        return "pending"
    ok = sum(1 for r in done if not (r["scoring"].get("validation_failed")
                                     or r.get("infra_failed")
                                     or r.get("_integrity_violations")))
    j = sum(r.get("judge", {}).get("score") or 0 for r in done)
    cost = sum(r.get("cost_usd") or 0 for r in done)
    hours = sum(r.get("result", {}).get("elapsed_ms", 0) for r in done) / 3600000
    return f"**{ok}/{len(done)}** · judgeΣ {j} · ${cost:.2f} · {hours:.1f}h"


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
                    r"\b(?:git\s+(?:fetch|clone|ls-remote)|curl|wget)\b", action,
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
                    r"\b(?:git\s+(?:fetch|clone|ls-remote)|curl|wget)\b",
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
            network = tool == "webfetch" or (
                tool == "bash" and bool(re.search(
                    r"\b(?:git\s+(?:fetch|clone|ls-remote)|curl|wget)\b",
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
    providers = []
    for arg in sys.argv[1:]:
        label, pattern = arg.split("=", 1)
        records = load(pattern)
        for case_id, record in records.items():
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
                 f"cost; wall time (incl. env setup + verification). "
                 f"LEAK = upstream solution access, excluded from passes._\n")
    header = "| case path | " + " | ".join(l for l, _ in providers) + " |"
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
        f"_Cross-model × harness matrix. Each cell = pass-rate · judgeΣ · "
        f"cost · wall time._\n",
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

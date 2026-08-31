"""Fail if any recorded score came from less than the full judge panel.

A score is the mean of the whole panel or it is not a score. A record judged by
one model is not comparable to one judged by three, and a dead panel stores a 0
that reads exactly like a bad answer — that is how a passing case once shipped
with score 0. judges/llm_judge.py retries missing judges at judging time; this
is the post-hoc proof that the retries worked, and the way to find records
judged before that rule existed.

Handles both record shapes: one-shot (results[].judge) and long-run
(results[].turns[].judge).

Usage:
  .venv/bin/python scripts/audit_judges.py <results-dir-or-json> [...]
Exit 1 if any record is short a judge.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def valid(v: dict) -> bool:
    """Same rule as judges/llm_judge.py:_is_valid_verdict, on a stored verdict."""
    if v.get("parse_error") or not isinstance(v.get("score"), (int, float)):
        return False
    return not (float(v["score"]) == 0 and not str(v.get("reasoning") or "").strip())


def check(judge: dict, label: str, short: list, unknown: list) -> None:
    panel = judge.get("judges")
    if not panel:
        # Single-model judging predates the panel; nothing to audit against.
        unknown.append((label, judge.get("_judge_model") or "no panel recorded"))
        return
    ok = sum(1 for v in panel if valid(v))
    if ok < len(panel) or judge.get("_judge_incomplete"):
        missing = [v.get("model") for v in panel if not valid(v)]
        short.append((label, f"{ok}/{len(panel)} verdicts, missing {missing}, "
                             f"stored score {judge.get('score')}"))


def main() -> None:
    args = [Path(a) for a in sys.argv[1:]]
    if not args:
        raise SystemExit("usage: audit_judges.py <results-dir-or-json> [...]")
    files = []
    for a in args:
        if a.is_file():
            files.append(a)
            continue
        # Campaign results live one level under the out dir (out/<timestamp>/
        # results.json). rglob would also match test-runner caches inside an
        # agent workspace — vitest writes its own node_modules/.vite/.../
        # results.json, whose "results" is a list of lists.
        files += sorted(a.glob("*/results*.json")) + sorted(a.glob("results*.json"))

    short: list = []
    unknown: list = []
    judged = 0
    for f in files:
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        for r in data.get("results", []):
            base = f"{f}::{r.get('case_id') or r.get('sequence_id')}"
            for t in r.get("turns") or []:
                if t.get("judge"):
                    judged += 1
                    check(t["judge"], f"{base}#turn{t.get('turn')}", short, unknown)
            if r.get("judge"):
                judged += 1
                check(r["judge"], base, short, unknown)

    for label, why in unknown:
        print(f"UNAUDITABLE {label}: {why}")
    for label, why in short:
        print(f"SHORT-PANEL {label}: {why}")
    print(f"audited {judged} judgment(s): {len(short)} short, "
          f"{len(unknown)} unauditable")
    if short:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

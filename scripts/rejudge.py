"""Re-run the LLM judge for records whose judge output failed to parse.

The agent runs stay untouched — everything the judge needs (task prompt,
script logs, evidence) is already in results.json. Records are re-judged when
the stored judge result has a parse error or no usable score; scoring is then
recomputed and results.json rewritten (with a .bak backup).

Usage: .venv/bin/python scripts/rejudge.py <results.json> [case_id ...]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from judges.llm_judge import run_judge  # noqa: E402
from cli.main import build_task_prompt, default_judge_cfg, load_yaml  # noqa: E402
from scoring.aggregate import compute_efficiency_score, compute_final_score  # noqa: E402


def needs_rejudge(record: dict) -> bool:
    judge = record.get("judge", {})
    if judge.get("_judge_parse_error"):
        return True
    score = judge.get("score")
    if score is None or (score == 0 and not judge.get("reasoning")):
        return True
    # A zero-confidence verdict is a judge that could not assess (empty-input
    # stub), and score 0 on a validation-PASS run contradicts the objective
    # signal — both are re-judged rather than trusted.
    if judge.get("confidence") in (0, 0.0):
        return True
    validation_ok = record["scripts"]["validate"]["exit_code"] == 0
    return score == 0 and validation_ok


def main() -> None:
    results_path = Path(sys.argv[1])
    only = set(sys.argv[2:])
    repo_root = Path.cwd().resolve()

    data = json.loads(results_path.read_text())
    scoring_cfg = load_yaml(repo_root / "configs" / "scoring.yaml")
    efficiency_cfg = load_yaml(repo_root / "configs" / "efficiency.yaml")
    judge_cfg = default_judge_cfg(repo_root)

    case_files = {c["id"]: c for c in (
        yaml.safe_load(open(p)) for p in (repo_root / "cases").rglob("case.yaml")
    )}

    changed = 0
    for r in data["results"]:
        if only and r["case_id"] not in only:
            continue
        if not (only or needs_rejudge(r)):
            continue
        case = case_files[r["case_id"]]
        scripts = r["scripts"]
        evidence = r.get("evidence", "")
        # Records written before the evidence fix can carry a file list with no
        # diff content (snapshot cap starved build_evidence). The workspace
        # persists per run — regenerate the real diff from git when available.
        workdir = Path(r.get("workdir", ""))
        if "@@" not in evidence and (workdir / ".git").exists():
            # Exclude held-out test paths: validate.sh checks them out from the
            # gold commit AFTER the agent runs, so they are harness-applied and
            # must not be attributed to (or held against) the agent.
            excludes = [f":(exclude){t}" for t in case.get("meta", {}).get("test_paths", [])]
            git = subprocess.run(
                ["git", "-c", "safe.directory=*", "diff", "--", "."] + excludes,
                cwd=workdir, capture_output=True, text=True,
            )
            if git.returncode == 0 and git.stdout.strip():
                diff_text = git.stdout
                if len(diff_text) > 60_000:
                    diff_text = diff_text[:60_000] + "\n... [diff truncated]"
                evidence += "\n\n<evidence_diff_regenerated>\n" + diff_text + "\n</evidence_diff_regenerated>"
        payload = {
            "task": build_task_prompt(case),
            "prep_log": scripts["setup"]["stdout"] + scripts["setup"]["stderr"],
            "quality_log": scripts["quality"]["stdout"] + scripts["quality"]["stderr"],
            "validation_log": scripts["validate"]["stdout"] + scripts["validate"]["stderr"],
            "validation_exit_code": scripts["validate"]["exit_code"],
            "evidence_log": evidence,
        }
        meta = dict(judge_cfg)
        meta["repo_root"] = str(repo_root)
        print(f"[rejudge] {r['case_id']} ({r['setup']}) old_score={r['judge'].get('score')}")
        # Judge from the repo root: the persisted case workspace can be
        # root-owned (container-created), which breaks the judge session's
        # own bookkeeping and yields unparseable output.
        judge_out = run_judge(payload, meta, str(repo_root))
        print(f"[rejudge]   new_score={judge_out.get('score')}")
        r["judge"] = judge_out

        efficiency = compute_efficiency_score(
            r["result"]["elapsed_ms"], r["tokens"]["total"], r.get("cost_usd"), efficiency_cfg
        )
        validation_failed = scripts["validate"]["exit_code"] != 0
        raw_final = compute_final_score(float(judge_out.get("score", 0)), efficiency, scoring_cfg)
        penalty = float(scoring_cfg.get("validation_fail_penalty", 25.0)) if validation_failed else 0.0
        r["scoring"].update(
            {
                "efficiency_score": efficiency,
                "raw_final_score": raw_final,
                "validation_penalty": penalty,
                "final_score": round(max(0.0, raw_final - penalty), 2),
                "validation_failed": validation_failed,
            }
        )
        changed += 1

    if changed:
        shutil.copy(results_path, str(results_path) + ".bak")
        results_path.write_text(json.dumps(data, indent=2))
    print(f"[rejudge] updated {changed} record(s) in {results_path}")


if __name__ == "__main__":
    main()

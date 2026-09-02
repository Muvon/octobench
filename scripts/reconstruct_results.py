#!/usr/bin/env python3
"""Reconstruct a results.json from log dirs when the original run aborted
before writing results.json.

Walks a run directory (e.g. results-dsv4-opencode/20260808-063657/), reads
each case's logs/ dir, parses provider.raw.jsonl for tokens/exit/stdout,
reads setup/quality/validate logs, builds evidence from git diff, and
writes a results.json compatible with scripts/rejudge.py and
scripts/update_benchmark.py.

Usage:
  python3 scripts/reconstruct_results.py <run_dir> [--merge <results.json> ...]

The --merge files are merged in (later files override earlier by case_id),
and the combined output is written to <run_dir>/results.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

# Add repo root to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cli.main import load_yaml  # noqa: E402
from scoring.aggregate import compute_efficiency_score, compute_final_score  # noqa: E402


def parse_provider_raw(raw_text: str) -> dict:
    """Parse opencode provider.raw.jsonl to extract tokens, stdout, stderr, steps."""
    input_tokens = 0
    output_tokens = 0
    reasoning_tokens = 0
    cached_input = 0
    last_text = None
    tool_titles: list[str] = []
    step_count = 0
    first_ts = None
    last_ts = None

    for line in raw_text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        ts = obj.get("timestamp")
        if ts is not None:
            if first_ts is None:
                first_ts = ts
            last_ts = ts

        typ = obj.get("type")
        part = obj.get("part") or {}

        if typ == "step_finish":
            step_count += 1
            tokens = part.get("tokens") or {}
            input_tokens += int(tokens.get("input") or 0)
            output_tokens += int(tokens.get("output") or 0)
            reasoning_tokens += int(tokens.get("reasoning") or 0)
            cache = tokens.get("cache") or {}
            cached_input += int(cache.get("read") or 0)
        elif typ == "text":
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                last_text = text
        elif typ == "tool_use":
            title = part.get("title") if isinstance(part, dict) else None
            tool = part.get("tool")
            if tool:
                tool_titles.append(f"{tool}: {title or ''}".strip())

    total = input_tokens + output_tokens
    elapsed_ms = 0
    if first_ts and last_ts:
        elapsed_ms = int(last_ts - first_ts)

    return {
        "stdout": (last_text or "").strip(),
        "stderr": "",
        "exit_code": 0,  # opencode run exits 0 on success; logs confirm
        "elapsed_ms": elapsed_ms,
        "input_tokens": input_tokens or None,
        "cached_input_tokens": cached_input or None,
        "output_tokens": output_tokens or None,
        "reasoning_tokens": reasoning_tokens or None,
        "total_tokens": total or None,
        "tool_titles": tool_titles[-24:],
        "step_count": step_count,
    }


def read_log(path: Path) -> dict:
    """Read a script log file into a record dict."""
    if not path.exists():
        return {"exit_code": 0, "stdout": "", "stderr": "", "elapsed_ms": 0}
    stdout = path.read_text(errors="replace")
    # Exit code is not stored in the log; infer from stderr content
    # For validate.sh, non-zero exit means validation failed
    # We'll set exit_code based on whether stderr contains error indicators
    stderr_path = path.parent / path.name.replace(".stdout.", ".stderr.")
    stderr = stderr_path.read_text(errors="replace") if stderr_path.exists() else ""
    return {
        "exit_code": 0,  # Will be overridden for validate
        "stdout": stdout,
        "stderr": stderr,
        "elapsed_ms": 0,
    }


def infer_validate_exit(stdout: str, stderr: str) -> int:
    """Infer validate.sh exit code from output."""
    combined = (stdout + stderr).lower()
    # Common failure indicators
    if "failed" in combined and "test" in combined:
        return 1
    if "error" in combined and "compilation" in combined:
        return 1
    if "0 failures" in combined or "all tests passed" in combined:
        return 0
    if "ok" in combined and "fail" not in combined:
        return 0
    # If we see test failures
    if "failures:" in combined or "failed (" in combined:
        return 1
    # Default: assume pass if there's output
    return 0 if stdout.strip() else 1


def build_evidence_from_git(workdir: Path, test_paths: list) -> str:
    """Build evidence diff from git, excluding test paths."""
    if not (workdir / ".git").exists():
        return ""
    excludes = [f":(exclude){t}" for t in test_paths]
    git = subprocess.run(
        ["git", "-c", "safe.directory=*", "diff", "--", "."] + excludes,
        cwd=workdir, capture_output=True, text=True,
    )
    if git.returncode != 0 or not git.stdout.strip():
        return ""
    diff_text = git.stdout
    if len(diff_text) > 60_000:
        diff_text = diff_text[:60_000] + "\n... [diff truncated]"
    return diff_text


def reconstruct_run(run_dir: Path, repo_root: Path) -> list[dict]:
    """Walk a run directory and reconstruct results records."""
    # Load case files for case_id -> case.yaml mapping
    case_files = {}
    for cf in (repo_root / "cases").rglob("case.yaml"):
        try:
            case = yaml.safe_load(cf.read_text())
            cid = case.get("id", cf.parent.name)
            case_files[cid] = case
        except Exception:
            continue

    # Load models config for pricing
    models_cfg = load_yaml(repo_root / "configs" / "models.yaml")
    scoring_cfg = load_yaml(repo_root / "configs" / "scoring.yaml")
    efficiency_cfg = load_yaml(repo_root / "configs" / "efficiency.yaml")

    records = []
    for case_dir in sorted(run_dir.iterdir()):
        if not case_dir.is_dir():
            continue
        case_id = case_dir.name
        # Find the provider setup dir
        setup_dirs = [d for d in case_dir.iterdir() if d.is_dir()]
        if not setup_dirs:
            continue
        setup_dir = setup_dirs[0]  # opencode__deepseek-v4-flash
        setup_name = setup_dir.name
        logs_dir = setup_dir / "logs"
        workspace = setup_dir / "workspace"

        if not logs_dir.exists():
            print(f"[reconstruct] SKIP {case_id}: no logs dir")
            continue

        # Parse provider raw
        raw_path = logs_dir / "provider.raw.jsonl"
        if not raw_path.exists():
            print(f"[reconstruct] SKIP {case_id}: no provider.raw.jsonl")
            continue
        raw_text = raw_path.read_text(errors="replace")
        provider_data = parse_provider_raw(raw_text)

        # Read script logs
        setup_log = read_log(logs_dir / "setup.stdout.log")
        quality_log = read_log(logs_dir / "quality.stdout.log")
        validate_log = read_log(logs_dir / "validate.stdout.log")

        # Infer exit codes
        setup_log["exit_code"] = (
            0 if setup_log["stdout"].strip() or not setup_log["stderr"].strip() else 1
        )
        # If setup stderr has "error" or "failed", mark as failed
        setup_err = setup_log["stderr"].lower()
        if "could not be resolved" in setup_err or "error" in setup_err and "install" in setup_err:
            setup_log["exit_code"] = 1

        validate_log["exit_code"] = infer_validate_exit(
            validate_log["stdout"], validate_log["stderr"]
        )

        # Build evidence
        case = case_files.get(case_id, {})
        test_paths = case.get("meta", {}).get("test_paths", [])
        evidence_diff = build_evidence_from_git(workspace, test_paths)

        # Build provider evidence
        provider_evidence_parts = []
        if provider_data["stdout"]:
            provider_evidence_parts.append("FINAL MESSAGE:\n" + provider_data["stdout"][-2000:])
        if provider_data["tool_titles"]:
            provider_evidence_parts.append(
                "TOOL CALLS (tail):\n"
                + "\n".join(f"- {c}" for c in provider_data["tool_titles"])
            )
        provider_evidence = "\n\n".join(provider_evidence_parts)

        evidence_parts = []
        if provider_evidence:
            evidence_parts.append(
                "<provider_evidence>\n"
                + provider_evidence.strip()
                + "\n</provider_evidence>"
            )
        if evidence_diff:
            evidence_parts.append(
                "<evidence_diff>\n"
                + evidence_diff.strip()
                + "\n</evidence_diff>"
            )
        evidence = "\n\n".join(evidence_parts)

        # Compute cost
        pricing = models_cfg.get("models", {}).get("deepseek-v4-flash", {}).get("pricing")
        cost = None
        if pricing and provider_data["input_tokens"]:
            # Use compute_cost from cli.main
            from cli.main import compute_cost
            cost = compute_cost(
                provider_data["input_tokens"],
                provider_data["cached_input_tokens"],
                provider_data["output_tokens"],
                pricing,
            )

        # Build the record
        record = {
            "case_id": case_id,
            "setup": setup_name,
            "provider": "opencode",
            "model": "deepseek-v4-flash",
            "provider_model": "alibaba/deepseek-v4-flash-0731",
            "runner": "provider",
            "executor": "docker",
            "result": {
                "stdout": provider_data["stdout"],
                "stderr": provider_data["stderr"],
                "exit_code": provider_data["exit_code"],
                "elapsed_ms": provider_data["elapsed_ms"],
            },
            "tokens": {
                "input": provider_data["input_tokens"],
                "cached_input": provider_data["cached_input_tokens"],
                "output": provider_data["output_tokens"],
                "reasoning": provider_data["reasoning_tokens"],
                "total": provider_data["total_tokens"],
            },
            "cost_usd": cost,
            "scripts": {
                "setup": setup_log,
                "quality": quality_log,
                "validate": validate_log,
            },
            "evidence": evidence,
            "evidence_diff": evidence_diff,
            "provider_evidence": provider_evidence,
            "workdir": str(workspace.resolve()),
            "judge": {
                "score": 0,
                "reasoning": "All panel judges failed to produce a verdict",
                "issues": ["reconstructed: judge not yet run"],
                "confidence": 0.0,
                "_judge_parse_error": True,
            },
            "scoring": {},
        }

        # Compute scoring
        efficiency = compute_efficiency_score(
            record["result"]["elapsed_ms"],
            record["tokens"]["total"],
            record.get("cost_usd"),
            efficiency_cfg,
        )
        validation_failed = validate_log["exit_code"] != 0
        raw_final = compute_final_score(0.0, efficiency, scoring_cfg)
        penalty = 0.0
        if validation_failed:
            penalty = float(scoring_cfg.get("validation_fail_penalty", 25.0))
        record["scoring"] = {
            "efficiency_score": efficiency,
            "raw_final_score": raw_final,
            "validation_penalty": penalty,
            "final_score": round(max(0.0, raw_final - penalty), 2),
            "validation_failed": validation_failed,
            "judge_weight": scoring_cfg.get("judge_weight", 0.85),
            "efficiency_weight": scoring_cfg.get("efficiency_weight", 0.15),
        }

        records.append(record)
        print(f"[reconstruct] {case_id}: steps={provider_data['step_count']} "
              f"tokens={provider_data['total_tokens']} validate_exit={validate_log['exit_code']}")

    return records


def merge_results(main_records: list[dict], merge_files: list[Path]) -> list[dict]:
    """Merge records from multiple results.json files. Later files override by case_id."""
    by_id = {r["case_id"]: r for r in main_records}
    for mf in merge_files:
        if not mf.exists():
            print(f"[merge] SKIP {mf}: not found")
            continue
        data = json.loads(mf.read_text())
        for r in data.get("results", []):
            by_id[r["case_id"]] = r  # Override with rerun data
            print(f"[merge] {r['case_id']}: overridden from {mf.name}")
    return list(by_id.values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "run_dir", help="Original run directory (e.g. results-dsv4-opencode/20260808-063657)"
    )
    parser.add_argument(
        "--merge", nargs="*", default=[],
        help="Additional results.json files to merge in (override by case_id)",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = repo_root / run_dir

    print(f"[reconstruct] scanning {run_dir}")
    records = reconstruct_run(run_dir, repo_root)
    print(f"[reconstruct] built {len(records)} records from run dir")

    merge_files = [Path(m) if Path(m).is_absolute() else repo_root / m for m in args.merge]
    if merge_files:
        records = merge_results(records, merge_files)
        print(f"[reconstruct] merged to {len(records)} total records")

    # Sort by case_id for stable output
    records.sort(key=lambda r: r["case_id"])

    out_path = run_dir / "results.json"
    with open(out_path, "w") as f:
        json.dump({"results": records}, f, indent=2)
    print(f"[reconstruct] wrote {out_path} ({len(records)} records)")


if __name__ == "__main__":
    main()

"""Re-run infra-failed records of a results.json and merge the retries in.

Infra-failed = provider crashed (infra_failed flag) or setup.sh failed — cases
where the agent never got a fair attempt. Genuine validation failures are NOT
retried. Each failed case is re-run via cli.main with the same provider config;
the fresh record replaces the failed one in results.json (backup kept).

Usage: .venv/bin/python scripts/rerun_failed.py <results.json> <run-matrix.yaml> [max_retries]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


def infra_failed(record: dict) -> bool:
    if record.get("infra_failed"):
        return True
    return record["scripts"]["setup"]["exit_code"] != 0


def find_case_dir(repo_root: Path, case_id: str) -> Path:
    for p in (repo_root / "cases").rglob("case.yaml"):
        if yaml.safe_load(open(p)).get("id") == case_id:
            return p.parent
    raise RuntimeError(f"case dir not found for {case_id}")


def main() -> None:
    results_path = Path(sys.argv[1]).resolve()
    matrix = sys.argv[2]
    max_retries = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    repo_root = Path.cwd().resolve()

    for attempt in range(1, max_retries + 1):
        data = json.loads(results_path.read_text())
        failed = [r for r in data["results"] if infra_failed(r)]
        if not failed:
            print("[rerun] no infra-failed records")
            return
        print(f"[rerun] attempt {attempt}: {len(failed)} infra-failed case(s)")
        for r in failed:
            case_dir = find_case_dir(repo_root, r["case_id"])
            out_dir = results_path.parent.parent / "reruns"
            print(f"[rerun]   {r['case_id']} ({case_dir})")
            proc = subprocess.run(
                [
                    ".venv/bin/python", "-m", "cli.main", "run",
                    "--cases", str(case_dir),
                    "--config", matrix,
                    "--executor", "docker", "--image", "octobench-agent:latest",
                    "--out", str(out_dir), "--verbosity", "quiet",
                ],
                cwd=repo_root, capture_output=True, text=True,
            )
            rerun_files = sorted(out_dir.glob("*/results.json"))
            if not rerun_files:
                print(f"[rerun]   {r['case_id']}: rerun produced no results "
                      f"(exit={proc.returncode}); leaving record")
                continue
            rerun_data = json.loads(rerun_files[-1].read_text())
            match = [x for x in rerun_data["results"] if x["case_id"] == r["case_id"]]
            if not match:
                print(f"[rerun]   {r['case_id']}: no matching record in rerun output")
                continue
            fresh = match[0]
            data["results"] = [
                fresh if (x["case_id"] == r["case_id"] and x["setup"] == r["setup"]) else x
                for x in data["results"]
            ]
            print(f"[rerun]   {r['case_id']}: replaced "
                  f"(infra_failed={bool(fresh.get('infra_failed'))})")
        shutil.copy(results_path, str(results_path) + f".bak{attempt}")
        results_path.write_text(json.dumps(data, indent=2))

    remaining = [r for r in json.loads(results_path.read_text())["results"] if infra_failed(r)]
    print(f"[rerun] done; {len(remaining)} infra-failed record(s) remain")


if __name__ == "__main__":
    main()

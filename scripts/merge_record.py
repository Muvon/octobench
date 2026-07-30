"""Replace a case's record in a canonical results.json with a rerun's record.

Usage: .venv/bin/python scripts/merge_record.py <canonical.json> <rerun.json> <case_id>

Recomputes the fresh record's scoring (mirrors cli.main) and rewrites the
canonical file with a .premerge backup.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli.main import load_yaml  # noqa: E402
from scoring.aggregate import compute_efficiency_score, compute_final_score  # noqa: E402


def main() -> None:
    canonical = Path(sys.argv[1])
    rerun = Path(sys.argv[2])
    case_id = sys.argv[3]
    repo_root = Path.cwd().resolve()

    scoring_cfg = load_yaml(repo_root / "configs" / "scoring.yaml")
    efficiency_cfg = load_yaml(repo_root / "configs" / "efficiency.yaml")

    fresh = [r for r in json.loads(rerun.read_text())["results"] if r["case_id"] == case_id]
    if not fresh:
        raise SystemExit(f"no {case_id} record in {rerun}")
    r = fresh[0]

    efficiency = compute_efficiency_score(
        r["result"]["elapsed_ms"], r["tokens"]["total"], r.get("cost_usd"), efficiency_cfg
    )
    validation_failed = r["scripts"]["validate"]["exit_code"] != 0
    raw_final = compute_final_score(
        float(r.get("judge", {}).get("score", 0)), efficiency, scoring_cfg
    )
    penalty = float(scoring_cfg.get("validation_fail_penalty", 25.0)) if validation_failed else 0.0
    r.setdefault("scoring", {}).update(
        {
            "efficiency_score": efficiency,
            "raw_final_score": raw_final,
            "validation_penalty": penalty,
            "final_score": round(max(0.0, raw_final - penalty), 2),
            "validation_failed": validation_failed,
        }
    )

    data = json.loads(canonical.read_text())
    before = sum(1 for x in data["results"] if x["case_id"] == case_id)
    data["results"] = [r if x["case_id"] == case_id else x for x in data["results"]]
    shutil.copy(canonical, str(canonical) + ".premerge")
    canonical.write_text(json.dumps(data, indent=2))
    print(f"merged {case_id} into {canonical} (replaced {before} record(s); "
          f"val={'FAIL' if validation_failed else 'PASS'} "
          f"judge={r.get('judge', {}).get('score')})")


if __name__ == "__main__":
    main()

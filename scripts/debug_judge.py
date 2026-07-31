"""Run the judge once for a stored record with the raw stream preserved.

Usage: .venv/bin/python scripts/debug_judge.py <results.json> <case_id> <out_dir>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli.main import build_task_prompt, default_judge_cfg  # noqa: E402
from judges.llm_judge import run_judge  # noqa: E402

import yaml  # noqa: E402

results, case_id, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
repo_root = Path.cwd().resolve()
Path(out_dir).mkdir(parents=True, exist_ok=True)

case = None
for p in (repo_root / "cases").rglob("case.yaml"):
    c = yaml.safe_load(open(p))
    if c.get("id") == case_id:
        case = c
        break
assert case, case_id

rec = [r for r in json.loads(Path(results).read_text())["results"]
       if r["case_id"] == case_id][0]
scripts = rec["scripts"]
payload = {
    "task": build_task_prompt(case),
    "prep_log": scripts["setup"]["stdout"] + scripts["setup"]["stderr"],
    "quality_log": scripts["quality"]["stdout"] + scripts["quality"]["stderr"],
    "validation_log": scripts["validate"]["stdout"] + scripts["validate"]["stderr"],
    "evidence_log": rec.get("evidence", ""),
}
meta = dict(default_judge_cfg(repo_root))
meta["io_dir"] = out_dir
meta["repo_root"] = str(repo_root)
out = run_judge(payload, meta, str(repo_root))
print("score:", out.get("score"), "parse_error:", out.get("_judge_parse_error"))
Path(out_dir, "judge.raw.txt").write_text(str(out.get("_judge_raw", "")))
print("raw saved; bytes:", len(str(out.get("_judge_raw", ""))))

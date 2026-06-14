"""SwebenchLiveAdapter: register the existing SWE-bench-Live flow as an adapter.

Thin wrapper over cli/swebench.py so the unified `cli.bench` runner can drive
coding cases through the same registry/scoring path as every other domain, while
the proven repo-in-image + FAIL_TO_PASS/PASS_TO_PASS logic stays in one place.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from benchmarks.base import BenchmarkAdapter, Instance, RunContext

from cli import swebench as sweb


def _size(row) -> int:
    return sum(len(sweb._as_list(row.get(k))) for k in ("FAIL_TO_PASS", "PASS_TO_PASS"))


class SwebenchLiveAdapter(BenchmarkAdapter):
    engine = "swebench_live"

    def requires_docker(self) -> bool:
        return True

    def load_instances(self, limit=None, split=None, instance_id=None) -> List[Instance]:
        split = split or self.config.get("split", "lite")
        rows = sweb.fetch_rows(split, length=100)
        if instance_id:
            rows = [r for r in rows if r.get("instance_id") == instance_id]
        else:
            rows.sort(key=_size)  # smallest first (fastest to prove the flow)
        if limit:
            rows = rows[:limit]
        return [
            Instance(
                id=r["instance_id"],
                prompt=r.get("problem_statement", ""),
                meta={"domain": self.domain, "split": split, "repo": r.get("repo")},
                raw=r,
            )
            for r in rows
        ]

    def run_instance(self, instance, target, ctx: RunContext, out_dir: Path) -> dict:
        # cli.swebench manages its own per-instance Docker image + log layout under
        # the run root; pass ctx.out_dir so it nests results consistently.
        rec = sweb.run_instance(
            instance.raw,
            target,
            ctx.repo_root,
            ctx.models_cfg,
            ctx.judge_cfg,
            ctx.out_dir,
            ctx.verbosity,
        )
        resolved = bool(rec.get("swebench", {}).get("resolved"))
        rec["verdict"] = {
            "objective": resolved,
            "mode": "swebench",
            "detail": rec.get("swebench", {}),
        }
        rec.setdefault("domain", self.domain)
        return rec

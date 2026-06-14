"""Benchmark adapter framework: shared types, executor wiring, and scoring.

Adapters turn an external benchmark into octobench runs. The unified runner
(cli/bench.py) iterates instances x run-targets, calls `adapter.run_instance`,
then `finalize_scoring` — reusing the same executor, judge, and scoring modules
as the local-case and SWE-bench-Live runners so results are directly comparable.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from runners.executor import DockerExecutor, Executor, HostExecutor
from scoring.aggregate import compute_efficiency_score, compute_final_score


@dataclass
class Instance:
    """One benchmark item (a question / task / issue)."""

    id: str
    prompt: str                       # the task text (includes choices for MCQ)
    gold: Any = None                  # expected answer for objective modes
    system_prompt: str = ""
    reference: str = ""               # reference answer (judge_text mode)
    rubric: str = ""                  # grading rubric (judge_text mode)
    constraints: Any = None           # IFEval-style constraint spec (constraint mode)
    choices: Optional[List[str]] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunContext:
    repo_root: Path
    models_cfg: Dict
    judge_cfg: Dict
    scoring_cfg: Dict
    efficiency_cfg: Dict
    out_dir: Path
    verbosity: str = "normal"
    executor_kind: str = "host"       # host | docker
    image: str = "octobench-agent:latest"

    @property
    def repo_config(self) -> Path:
        return self.repo_root / "configs" / "octomind" / "octomind.toml"


class BenchmarkAdapter(ABC):
    """Base class for benchmark adapters. Metadata comes from the YAML config."""

    #: engine key registered in benchmarks.registry
    engine: str = "base"

    def __init__(self, config: Dict):
        self.config = config or {}
        self.name: str = self.config.get("name", "benchmark")
        self.domain: str = self.config.get("domain", "")
        self.fit: str = self.config.get("fit", "")
        self.contamination: str = self.config.get("contamination", "")
        self.description: str = self.config.get("description", "")

    @abstractmethod
    def load_instances(
        self,
        limit: Optional[int] = None,
        split: Optional[str] = None,
        instance_id: Optional[str] = None,
    ) -> List[Instance]:
        """Return the instances to run (respecting limit/split/instance filters)."""

    @abstractmethod
    def run_instance(
        self,
        instance: Instance,
        target: Dict[str, str],
        ctx: RunContext,
        out_dir: Path,
    ) -> Dict:
        """Run one instance for one setup (provider+model); return a result record."""

    # --- shared helpers -----------------------------------------------------

    def requires_docker(self) -> bool:
        return False


def _safe_id(value: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9._-]+", "_", value or "")


def make_executor(
    ctx: RunContext,
    workspace: Path,
    case_dir: Path,
    case_id: str,
    provider_name: str,
) -> Executor:
    """Per-run executor: local subprocesses (host) or a fresh container (docker)."""
    if ctx.executor_kind == "docker":
        name = (
            f"ob-{_safe_id(case_id)[:22]}-{provider_name[:8]}-{int(time.time() * 1000)}"
        )
        return DockerExecutor(ctx.image, workspace, case_dir, ctx.repo_config, name)
    return HostExecutor(workspace, case_dir, ctx.repo_config)


def base_record(
    instance: Instance,
    target: Dict[str, str],
    ctx: RunContext,
    engine: str,
) -> Dict:
    """Common record skeleton shared by all adapters."""
    provider = target["provider"]
    benchmark_model = target["benchmark_model"]
    return {
        "case_id": instance.id,
        "source": engine,
        "setup": f"{provider}__{_safe_id(benchmark_model)}",
        "provider": provider,
        "model": benchmark_model,
        "provider_model": target["provider_model"],
        "runner": "bench",
        "executor": ctx.executor_kind,
        "domain": instance.meta.get("domain", ""),
        "result": {"stdout": "", "stderr": "", "exit_code": 0, "elapsed_ms": 0},
        "tokens": {
            "input": None,
            "cached_input": None,
            "output": None,
            "reasoning": None,
            "total": None,
        },
        "cost_usd": None,
        "scripts": {
            "setup": {"exit_code": 0},
            "quality": {"exit_code": 0},
            "validate": {"exit_code": 0},
        },
        "verdict": {"objective": None, "mode": "", "detail": {}},
        "judge": {"score": 0},
        "scoring": {},
    }


def apply_provider_result(record: Dict, pr, pricing: Optional[Dict]) -> None:
    """Copy provider telemetry (stdout/tokens/cost) into a record."""
    from scoring.aggregate import compute_cost

    record["result"] = {
        "stdout": pr.stdout,
        "stderr": pr.stderr,
        "exit_code": pr.exit_code,
        "elapsed_ms": pr.elapsed_ms,
    }
    record["tokens"] = {
        "input": pr.input_tokens,
        "cached_input": pr.cached_input_tokens,
        "output": pr.output_tokens,
        "reasoning": pr.reasoning_tokens,
        "total": pr.total_tokens,
    }
    record["cost_usd"] = (
        compute_cost(pr.input_tokens, pr.cached_input_tokens, pr.output_tokens, pricing)
        if pricing
        else None
    )


def set_verdict(record: Dict, objective: Optional[bool], mode: str, detail: Dict) -> None:
    record["verdict"] = {"objective": objective, "mode": mode, "detail": detail}
    # Mirror the objective gate onto scripts.validate so summary.py shows pass/FAIL.
    if objective is not None:
        record["scripts"]["validate"] = {"exit_code": 0 if objective else 1}


def finalize_scoring(record: Dict, ctx: RunContext) -> None:
    """Compute efficiency + final score. Objective verdicts drive final_score
    (100/0, like SWE-bench-Live); judge-only verdicts use the weighted formula."""
    res = record.get("result", {})
    toks = record.get("tokens", {})
    eff = compute_efficiency_score(
        res.get("elapsed_ms"), toks.get("total"), record.get("cost_usd"), ctx.efficiency_cfg
    )
    judge_score = float((record.get("judge") or {}).get("score", 0) or 0)
    objective = (record.get("verdict") or {}).get("objective")

    if objective is None:
        validation_failed = record.get("scripts", {}).get("validate", {}).get("exit_code", 0) != 0
        raw_final = compute_final_score(judge_score, eff, ctx.scoring_cfg)
        penalty = (
            float(ctx.scoring_cfg.get("validation_fail_penalty", 25.0))
            if validation_failed
            else 0.0
        )
        record["scoring"] = {
            "efficiency_score": eff,
            "raw_final_score": raw_final,
            "validation_penalty": penalty,
            "final_score": round(max(0.0, raw_final - penalty), 2),
            "validation_failed": validation_failed,
            "judge_weight": ctx.scoring_cfg.get("judge_weight", 0.85),
            "efficiency_weight": ctx.scoring_cfg.get("efficiency_weight", 0.15),
        }
    else:
        resolved = bool(objective)
        record["scoring"] = {
            "resolved": resolved,
            "judge_score": judge_score,
            "efficiency_score": eff,
            "final_score": 100.0 if resolved else 0.0,
            "validation_failed": not resolved,
        }

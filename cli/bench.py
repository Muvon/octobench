"""Unified multi-domain benchmark runner.

Runs any registered benchmark (configs/benchmarks/*.yaml) across the configured
agent SETUPS (provider + model), reusing the same executor, judge, and scoring as
the local-case and SWE-bench-Live runners. Results land in results-bench/ in the
standard format, viewable with scripts/summary.py.

Examples:
  python3 -m cli.bench --list
  python3 -m cli.bench --benchmark gpqa_diamond --limit 5
  python3 -m cli.bench --benchmark ifeval --limit 10 --providers claude,octomind
  python3 -m cli.bench --benchmark swebench_live --split lite --limit 1
  python3 -m cli.bench --benchmark cybench --executor docker   # needs upstream image
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from benchmarks.base import RunContext, finalize_scoring
from benchmarks.registry import build_adapter, list_benchmarks
from cli.main import (
    default_judge_cfg,
    load_yaml,
    log,
    parse_run_matrix_config,
    resolve_provider_model,
    safe_id,
)

_READY = {"qa": "data", "docker_task": "needs-image", "swebench_live": "docker"}

DEFAULT_SCORING = {"judge_weight": 0.85, "efficiency_weight": 0.15, "validation_fail_penalty": 25.0}
DEFAULT_EFFICIENCY = {
    "latency_ms": 8000,
    "cost_usd": 0.2,
    "tps": 50,
    "weight_latency": 0.4,
    "weight_cost": 0.4,
    "weight_tps": 0.2,
}


def _print_list(repo_root: Path) -> None:
    rows = list_benchmarks(repo_root)
    if not rows:
        print("No benchmarks found under configs/benchmarks/")
        return
    hdr = f"{'name':26}{'domain':30}{'engine':14}{'fit':18}{'contam':8}{'ready':12}"
    print(hdr)
    print("-" * len(hdr))
    cur = None
    for name, cfg in rows:
        dom = cfg.get("domain", "")
        if dom != cur:
            cur = dom
        print(
            f"{name[:25]:26}{dom[:29]:30}{cfg.get('engine', '?')[:13]:14}"
            f"{cfg.get('fit', '')[:17]:18}{cfg.get('contamination', '')[:7]:8}"
            f"{_READY.get(cfg.get('engine', ''), '?')[:11]:12}"
        )
    print(
        "\nready: data=runs now from HF/inline (needs model API key); "
        "needs-image=needs the upstream Docker image; docker=SWE-bench-Live images.\n"
        "Run one with:  python3 -m cli.bench --benchmark <name> --limit N"
    )


def _build_run_targets(args, repo_root: Path, models_cfg: dict):
    if args.providers is not None or args.models is not None:
        from cli.main import parse_providers, parse_selected_models

        providers = parse_providers(args.providers)
        models = parse_selected_models(models_cfg, args.models)
        return [
            {
                "provider": p,
                "benchmark_model": m,
                "provider_model": resolve_provider_model(models_cfg, m, p),
            }
            for p in providers
            for m in models
        ]
    # run-matrix config: explicit bench matrix, else the default matrix.
    for candidate in (
        args.config,
        "configs/run-matrix.bench.yaml",
        "configs/run-matrix.yaml",
    ):
        if candidate and Path(candidate).exists():
            return parse_run_matrix_config(Path(candidate), models_cfg)
    raise RuntimeError("No run matrix found; pass --config or --providers/--models")


def main() -> None:
    p = argparse.ArgumentParser(prog="python3 -m cli.bench")
    p.add_argument("--benchmark", help="benchmark name (configs/benchmarks/<name>.yaml) or path")
    p.add_argument("--list", action="store_true", help="list available benchmarks and exit")
    p.add_argument("--limit", type=int, default=None, help="max instances to run")
    p.add_argument("--split", default=None, help="dataset split (benchmark-specific)")
    p.add_argument("--instance", default=None, help="run a single instance id")
    p.add_argument("--config", default=None, help="run-matrix config (provider/model pairs)")
    p.add_argument("--providers", default=None, help="comma-separated providers (cross-product)")
    p.add_argument("--models", default=None, help="comma-separated benchmark model keys")
    p.add_argument("--out", default="results-bench")
    p.add_argument("--scoring", default="configs/scoring.yaml")
    p.add_argument("--efficiency", default="configs/efficiency.yaml")
    p.add_argument("--executor", choices=["host", "docker"], default="host")
    p.add_argument("--image", default="octobench-agent:latest")
    p.add_argument(
        "--no-judge",
        action="store_true",
        help="skip the LLM judge (objective benches still score from their verdict)",
    )
    p.add_argument("--verbosity", choices=["quiet", "normal", "debug"], default="normal")
    args = p.parse_args()

    repo_root = Path.cwd().resolve()
    if args.list or not args.benchmark:
        _print_list(repo_root)
        return

    models_cfg = load_yaml(repo_root / "configs" / "models.yaml")
    judge_cfg = default_judge_cfg(repo_root)
    scoring_cfg = load_yaml(Path(args.scoring)) if Path(args.scoring).exists() else DEFAULT_SCORING
    efficiency_cfg = (
        load_yaml(Path(args.efficiency)) if Path(args.efficiency).exists() else DEFAULT_EFFICIENCY
    )

    adapter = build_adapter(repo_root, args.benchmark)
    if args.no_judge and hasattr(adapter, "run_judge_flag"):
        adapter.run_judge_flag = False

    # octomind runs a task-appropriate agent: its coding agent for coding engines,
    # its general assistant for non-coding tasks (QA / instruction-following). A
    # benchmark config may override via `octomind_agent`. (Read by providers/octomind.py)
    coding_engines = {"swebench_live", "docker_task"}
    octomind_agent = adapter.config.get("octomind_agent") or (
        "developer:general" if adapter.engine in coding_engines else "assistant:general"
    )
    os.environ["OCTOMIND_AGENT"] = octomind_agent

    run_targets = _build_run_targets(args, repo_root, models_cfg)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    run_root = Path(args.out) / timestamp
    run_root.mkdir(parents=True, exist_ok=True)

    ctx = RunContext(
        repo_root=repo_root,
        models_cfg=models_cfg,
        judge_cfg=judge_cfg,
        scoring_cfg=scoring_cfg,
        efficiency_cfg=efficiency_cfg,
        out_dir=run_root,
        verbosity=args.verbosity,
        executor_kind=args.executor,
        image=args.image,
    )

    if adapter.requires_docker() and args.executor != "docker":
        log(
            f"[bench] note: '{adapter.name}' ({adapter.engine}) runs in Docker regardless "
            "of --executor (it builds its own per-instance container).",
            args.verbosity,
            "normal",
        )

    instances = adapter.load_instances(
        limit=args.limit, split=args.split, instance_id=args.instance
    )
    log(
        f"[bench] benchmark={adapter.name} domain={adapter.domain} engine={adapter.engine} "
        f"octomind_agent={octomind_agent} instances={len(instances)} setups={len(run_targets)}",
        args.verbosity,
        "normal",
    )
    if not instances:
        print("No instances loaded (check --split/--instance/--limit or dataset availability).")
        return

    results = []
    for inst in instances:
        used: dict[str, int] = {}
        for target in run_targets:
            base = f"{target['provider']}__{safe_id(target['benchmark_model'])}"
            idx = used.get(base, 0)
            used[base] = idx + 1
            setup_name = base if idx == 0 else f"{base}__{idx + 1}"
            per_dir = run_root / safe_id(inst.id) / setup_name
            per_dir.mkdir(parents=True, exist_ok=True)
            try:
                rec = adapter.run_instance(inst, target, ctx, per_dir)
            except Exception as e:  # one instance must not sink the batch
                log(f"[bench] ERROR {inst.id} {target['provider']}: {e}", args.verbosity, "normal")
                continue
            finalize_scoring(rec, ctx)
            results.append(rec)
            sc = rec.get("scoring", {})
            log(
                f"[bench] done {inst.id} {target['provider']} "
                f"final={sc.get('final_score')} resolved={sc.get('resolved')} "
                f"judge={rec.get('judge', {}).get('score')}",
                args.verbosity,
                "normal",
            )

    out_path = run_root / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"benchmark": adapter.name, "domain": adapter.domain, "results": results},
            f,
            indent=2,
        )
    print(f"OK {len(results)} run(s). Results: {out_path}")
    print(f"View: python3 scripts/summary.py {out_path}")


if __name__ == "__main__":
    main()

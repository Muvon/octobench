"""Multi-turn long-run benchmark runner.

Runs a sequence of related tasks (one per commit) in a single agent session,
mimicking continuous user turns. The agent's source changes persist across
turns; validation checks out only the gold test files per turn.

Usage:
    python3 -m cli.longrun run \
        --sequence cases/dev/longrun/rust/tokio \
        --providers codex,octomind \
        --verbosity normal
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from cli.main import (
    clean_workspace,
    default_judge_cfg,
    diff_snapshots,
    ensure_workspace,
    install_guardrails,
    seal_network,
    unseal_network,
    load_yaml,
    log,
    make_executor,
    parse_providers,
    parse_selected_models,
    resolve_provider_model,
    run_case_script,
    safe_id,
    snapshot_files,
    write_text,
)
from judges.llm_judge import run_judge
from providers.factory import get_provider
from runners.executor import Executor
from scoring.aggregate import (
    TOKEN_SEMANTICS,
    compute_cost,
    compute_efficiency_score,
    compute_final_score,
)


def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _build_turn_prompt(system_prompt: str, instruction: str, is_first_turn: bool) -> str:
    if is_first_turn:
        return f"System:\n{system_prompt}\n\nInstruction:\n{instruction}\n"
    return f"{instruction}\n"


def _validate_turn(
    executor: Executor,
    repo_url: str,
    gold_sha: str,
    test_paths: List[str],
    test_command: str,
    verbosity: str,
) -> Dict[str, Any]:
    """Fetch gold test files, run tests, then clean up.

    After running tests, gold test files are restored to HEAD (base_sha) and
    origin is removed — so the agent never sees gold tests or can fetch gold
    commits in subsequent turns.
    """
    paths_arg = "\n".join(test_paths)
    script = (
        f"set -euo pipefail\n"
        f"git remote add origin {repo_url} 2>/dev/null || true\n"
        f"git fetch -q --depth 1 origin {gold_sha}\n"
    )
    for tp in test_paths:
        script += f'git checkout -q {gold_sha} -- "{tp}"\n'
    # Run test without set -e so we capture the exit code.
    script += "set +e\n"
    script += f"{test_command}\n"
    script += "__test_exit=$?\n"
    script += "set -e\n"
    # Clean up: restore test files to HEAD so gold tests don't leak into
    # the next turn's workspace. `git checkout <gold> -- <path>` STAGES new
    # files, so unstage first — otherwise the gold blob survives in the index
    # (recoverable via `git show :<path>`) even after rm. Remove origin so
    # the agent can't fetch gold commits during its work phase.
    for tp in test_paths:
        script += f'git reset -q HEAD -- "{tp}" 2>/dev/null || true\n'
        script += f'git checkout -q HEAD -- "{tp}" 2>/dev/null || rm -f "{tp}"\n'
    script += 'git remote remove origin 2>/dev/null || true\n'
    script += "exit $__test_exit\n"

    env = {"REPO_URL": repo_url, "GOLD_SHA": gold_sha, "TEST_PATHS": paths_arg}
    log(f"[longrun] validate turn: gold={gold_sha[:12]}", verbosity, "normal")
    res = executor.run(["bash", "-c", script], env_overrides=env)
    log(
        f"[longrun] validate exit={res.exit_code} elapsed_ms",
        verbosity,
        "normal",
    )
    return {
        "exit_code": res.exit_code,
        "stdout": res.stdout,
        "stderr": res.stderr,
    }


def _run_sequence(
    sequence: Dict[str, Any],
    sequence_dir: Path,
    provider_name: str,
    benchmark_model: str,
    provider_model: str,
    run_dir: Path,
    args: argparse.Namespace,
    judge_cfg: Dict,
    scoring_cfg: Dict,
    efficiency_cfg: Dict,
    pricing: Dict,
    verbosity: str,
) -> Dict[str, Any]:
    """Run one full multi-turn sequence for a single provider+model."""
    seq_id = sequence.get("id", sequence_dir.name)
    system_prompt = sequence.get("system_prompt", "")
    turns = sequence.get("turns", [])
    max_turns = getattr(args, "max_turns", None)
    if max_turns:
        turns = turns[:max_turns]
    repo_url = sequence.get("meta", {}).get("repo", "")
    repo_root = Path.cwd().resolve()
    repo_config = repo_root / "configs" / "octomind" / "octomind.toml"

    provider_impl = get_provider(provider_name)
    workdir = ensure_workspace(sequence_dir, run_dir)
    workdir_abs = workdir.resolve()
    executor = make_executor(
        args, workdir_abs, sequence_dir, repo_config, seq_id, provider_name
    )

    turn_results: List[Dict[str, Any]] = []
    session_id: Optional[str] = None
    # Stable session name across all turns — octomind uses --name as the
    # session identifier, so it must not change between turns.
    session_name = (
        f"lr-{safe_id(seq_id)[:20]}-{provider_name[:8]}-"
        f"{safe_id(benchmark_model)[:12]}-{int(time.time())}"
    )
    try:
        # Phase 1: one-time setup (checks out base_sha, prepares env).
        setup_log = run_case_script(executor, "setup.sh", verbosity)
        if setup_log["exit_code"] != 0:
            log(
                f"[longrun] setup FAILED exit={setup_log['exit_code']}",
                verbosity,
                "normal",
            )
            return {
                "sequence_id": seq_id,
                "provider": provider_name,
                "benchmark_model": benchmark_model,
                "provider_model": provider_model,
                "setup": {
                    "exit_code": setup_log["exit_code"],
                    "stdout": setup_log["stdout"],
                    "stderr": setup_log["stderr"],
                },
                "turns": [],
                "error": "setup_failed",
            }

        # Phase 2: iterate turns.
        for idx, turn in enumerate(turns):
            turn_name = turn.get("name", f"turn_{idx + 1}")
            instruction = turn.get("instruction", "")
            gold_sha = turn.get("gold_sha", "")
            test_paths = turn.get("test_paths", [])
            test_command = turn.get("test_command", "")
            is_first = idx == 0

            log(
                f"[longrun] turn {idx + 1}/{len(turns)}: {turn_name}",
                verbosity,
                "normal",
            )

            prompt = _build_turn_prompt(system_prompt, instruction, is_first)
            install_guardrails(executor)
            sealed = os.environ.get("OCTOBENCH_SEAL_NETWORK") == "1"
            if sealed:
                seal_network(executor)
            before = snapshot_files(executor.workspace_host_path())

            # session_name is stable across turns (set once above).

            try:
                provider_result = provider_impl.run_task(
                    prompt=prompt,
                    workdir=executor.container_workspace(),
                    provider_model=provider_model,
                    session_name=session_name,
                    executor=executor,
                    resume_session_id=session_id,
                )
            finally:
                # _validate_turn fetches gold tests from the same hosts.
                if sealed:
                    unseal_network(executor)
            session_id = provider_result.session_id or session_id

            if provider_result.exit_code != 0:
                err_tail = (provider_result.stderr or "").strip() or (
                    provider_result.stdout or ""
                ).strip()
                log(
                    f"[longrun] PROVIDER-FAILED turn={idx + 1} exit={provider_result.exit_code}"
                    + (f" details={err_tail[:200]}" if err_tail else ""),
                    verbosity,
                    "normal",
                )

            after = snapshot_files(executor.workspace_host_path())
            diff = diff_snapshots(before, after)

            # Validate this turn's gold tests.
            validation = _validate_turn(
                executor,
                repo_url,
                gold_sha,
                test_paths,
                test_command,
                verbosity,
            )

            # Per-turn logs.
            logs_dir = run_dir / "turns" / f"turn_{idx + 1}" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            write_text(logs_dir / "provider.stdout.log", provider_result.stdout or "")
            write_text(logs_dir / "provider.stderr.log", provider_result.stderr or "")
            write_text(logs_dir / "provider.raw.jsonl", provider_result.raw_output or "")
            write_text(logs_dir / "validate.stdout.log", validation["stdout"])
            write_text(logs_dir / "validate.stderr.log", validation["stderr"])

            # Judge this turn.
            evidence_parts: List[str] = []
            provider_evidence = provider_impl.build_provider_evidence(provider_result)
            if provider_evidence:
                evidence_parts.append(
                    "<provider_evidence>\n"
                    + provider_evidence.strip()
                    + "\n</provider_evidence>"
                )
            diff_text = _diff_text(diff)
            if diff_text:
                evidence_parts.append(
                    "<evidence_diff>\n" + diff_text + "\n</evidence_diff>"
                )

            judge_payload = {
                "task": prompt,
                "prep_log": setup_log["stdout"] + setup_log["stderr"],
                "quality_log": "",
                "validation_log": validation["stdout"] + validation["stderr"],
                "validation_exit_code": validation["exit_code"],
                "evidence_log": "\n\n".join(p for p in evidence_parts if p),
            }
            judge_meta = dict(judge_cfg)
            judge_meta["io_dir"] = str(logs_dir.resolve())
            judge_meta["repo_root"] = str(repo_root)
            judge_out = run_judge(judge_payload, judge_meta, str(workdir_abs))
            write_text(logs_dir / "judge.raw.log", str(judge_out.get("_judge_raw", "")))

            tokens_total = provider_result.total_tokens or 0
            cost_usd = provider_result.provider_cost_usd
            if cost_usd is None:
                cost_usd = compute_cost(
                    provider_result.input_tokens,
                    provider_result.cached_input_tokens,
                    provider_result.output_tokens,
                    pricing,
                    provider_result.reasoning_tokens,
                )

            efficiency = compute_efficiency_score(
                provider_result.elapsed_ms, tokens_total, cost_usd, efficiency_cfg
            )
            judge_score = float(judge_out.get("score", 0))
            raw_final = compute_final_score(judge_score, efficiency, scoring_cfg)
            validation_failed = validation["exit_code"] != 0
            penalty = float(scoring_cfg.get("validation_fail_penalty", 25.0))
            final_score = round(max(0.0, raw_final - (penalty if validation_failed else 0)), 2)

            turn_results.append(
                {
                    "turn": idx + 1,
                    "name": turn_name,
                    "instruction": instruction,
                    "provider": {
                        "exit_code": provider_result.exit_code,
                        "elapsed_ms": provider_result.elapsed_ms,
                        "session_id": provider_result.session_id,
                        "stdout": (provider_result.stdout or "")[-2000:],
                    },
                    "tokens": {
                        "semantics": TOKEN_SEMANTICS,
                        "input": provider_result.input_tokens,
                        "cached_input": provider_result.cached_input_tokens,
                        "output": provider_result.output_tokens,
                        "reasoning": provider_result.reasoning_tokens,
                        "total": tokens_total,
                    },
                    "cost_usd": cost_usd,
                    "validation": {
                        "exit_code": validation["exit_code"],
                        "passed": not validation_failed,
                    },
                    "judge": judge_out,
                    "scoring": {
                        "efficiency_score": efficiency,
                        "raw_final_score": raw_final,
                        "final_score": final_score,
                        "validation_failed": validation_failed,
                    },
                }
            )
            verdict = "PASS" if not validation_failed else "FAIL"
            log(
                f"[longrun] turn {idx + 1} done: validate={verdict} "
                f"score={final_score}",
                verbosity,
                "normal",
            )

    finally:
        # A sequence keeps its checkout for all its turns, so it can only be
        # dropped here. Rust/C++ build trees reach tens of GB each; without this
        # a 20-sequence campaign needs more disk than the box has. Turn logs,
        # diffs and scores live under run_dir/turns and are unaffected.
        clean_workspace(executor, workdir_abs, seq_id, verbosity)
        executor.close()

    # Aggregate sequence-level metrics.
    total_turns = len(turn_results)
    passed = sum(1 for t in turn_results if t["validation"]["passed"])
    total_cost = sum(t["cost_usd"] or 0 for t in turn_results)
    total_tokens = sum(t["tokens"]["total"] or 0 for t in turn_results)
    # Each turn is valued separately; the sequence's score is the SUM of its
    # turn scores (avg kept for cross-length comparability).
    sum_score = sum(t["scoring"]["final_score"] for t in turn_results)
    avg_score = sum_score / total_turns if total_turns else 0

    return {
        "sequence_id": seq_id,
        "provider": provider_name,
        "benchmark_model": benchmark_model,
        "provider_model": provider_model,
        "setup": {
            "exit_code": setup_log["exit_code"],
        },
        "turns": turn_results,
        "aggregate": {
            "total_turns": total_turns,
            "passed": passed,
            "pass_rate": round(passed / total_turns, 4) if total_turns else 0,
            "sum_final_score": round(sum_score, 2),
            "avg_final_score": round(avg_score, 2),
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
        },
    }


def _diff_text(diff: Dict) -> str:
    lines: List[str] = []
    for f in sorted(diff.get("added", [])):
        lines.append(f"+ {f}")
    for f in sorted(diff.get("deleted", [])):
        lines.append(f"- {f}")
    for f in sorted(diff.get("modified", [])):
        lines.append(f"~ {f}")
    return "\n".join(lines)


def _find_sequence_files(args) -> List[Path]:
    """Resolve --sequence/--sequences into a list of sequence.yaml paths."""
    sequence_files: List[Path] = []
    if getattr(args, "sequences", None):
        root = Path(args.sequences)
        sequence_files = list(root.rglob("sequence.yaml"))
    elif getattr(args, "sequence", None):
        p = Path(args.sequence)
        if p.is_dir():
            p = p / "sequence.yaml"
        if not p.exists():
            raise FileNotFoundError(f"Sequence file not found: {p}")
        sequence_files = [p]
    else:
        raise RuntimeError("Provide --sequence or --sequences")
    if not sequence_files:
        raise RuntimeError("No sequence.yaml files found")
    return sequence_files


_REQUIRED_TOP = ["id", "name", "language", "system_prompt", "meta", "turns"]
_REQUIRED_TURN = ["name", "instruction", "gold_sha", "test_paths", "test_command"]
_REQUIRED_META = ["repo", "base_sha"]


def _cmd_validate(args: argparse.Namespace) -> None:
    """Dry-run validation: parse every sequence.yaml and check required fields."""
    sequence_files = _find_sequence_files(args)
    errors: List[str] = []
    ok = 0

    for sf in sorted(sequence_files):
        try:
            data = yaml.safe_load(sf.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{sf}: PARSE ERROR: {exc}")
            continue

        cid = data.get("id", sf.parent.name)
        case_errs: List[str] = []

        for k in _REQUIRED_TOP:
            if k not in data:
                case_errs.append(f"missing top-level key '{k}'")

        meta = data.get("meta", {})
        for k in _REQUIRED_META:
            if k not in meta:
                case_errs.append(f"missing meta.{k}")

        turns = data.get("turns", [])
        if not isinstance(turns, list) or len(turns) == 0:
            case_errs.append("turns is empty or not a list")
            turns = []
        elif len(turns) < 5:
            case_errs.append(f"has {len(turns)} turns (expected >= 5)")

        for i, t in enumerate(turns):
            for k in _REQUIRED_TURN:
                if k not in t:
                    case_errs.append(f"turn {i + 1}: missing '{k}'")
            sha = t.get("gold_sha", "")
            if sha and len(str(sha)) != 40:
                case_errs.append(f"turn {i + 1}: gold_sha len={len(str(sha))} (expected 40)")
            tp = t.get("test_paths", [])
            if not isinstance(tp, list) or len(tp) == 0:
                case_errs.append(f"turn {i + 1}: test_paths empty")
            tc = t.get("test_command", "")
            if not str(tc).strip():
                case_errs.append(f"turn {i + 1}: test_command empty")

        if case_errs:
            for e in case_errs:
                errors.append(f"{cid}: {e}")
        else:
            ok += 1
            print(f"  OK  {cid:45s} turns={len(turns)} lang={data.get('language')}")

    print(f"\n=== {ok}/{len(sequence_files)} cases valid ===")
    if errors:
        print(f"\n{len(errors)} ERROR(S):")
        for e in errors:
            print(f"  FAIL {e}")
        sys.exit(1)
    print("All cases structurally valid")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python3 -m cli.longrun")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Shared --sequence/--sequences args for both subcommands.
    def _add_seq_args(p):
        p.add_argument(
            "--sequence",
            help="Path to a sequence.yaml file or a directory containing one",
        )
        p.add_argument(
            "--sequences",
            default=None,
            help="Path to a directory tree containing multiple sequence.yaml files",
        )

    # validate: dry-run structural check (no providers, no execution).
    val_p = sub.add_parser("validate", help="Validate sequence.yaml files without running")
    _add_seq_args(val_p)

    # run: full multi-turn benchmark.
    run_p = sub.add_parser("run", help="Run a long-run sequence benchmark")
    _add_seq_args(run_p)
    run_p.add_argument("--providers", default=None)
    run_p.add_argument("--models", default=None)
    run_p.add_argument(
        "--config",
        default="configs/run-matrix.yaml",
        help="Run matrix config (used when --providers/--models not set)",
    )
    run_p.add_argument("--out", default="results-longrun")
    run_p.add_argument("--scoring", default="configs/scoring.yaml")
    run_p.add_argument("--efficiency", default="configs/efficiency.yaml")
    run_p.add_argument(
        "--verbosity", choices=["quiet", "normal", "debug"], default="normal"
    )
    run_p.add_argument(
        "--executor", choices=["host", "docker"], default="host"
    )
    run_p.add_argument("--image", default="octobench-agent:latest")
    run_p.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Run only the first N turns (for smoke testing / partial runs)",
    )

    args = parser.parse_args()

    if args.cmd == "validate":
        _cmd_validate(args)
        return

    if args.cmd != "run":
        return

    verbosity = args.verbosity
    repo_root = Path.cwd().resolve()
    models_path = repo_root / "configs" / "models.yaml"
    if not models_path.exists():
        raise RuntimeError(f"Missing required models config: {models_path}")
    models_cfg = load_yaml(models_path)
    judge_cfg = default_judge_cfg(repo_root)

    # Resolve run targets (providers × models).
    run_matrix_path = Path(args.config) if args.config else None
    if args.providers is not None or args.models is not None:
        selected_models = parse_selected_models(models_cfg, args.models)
        selected_providers = parse_providers(args.providers)
        run_targets = []
        for pn in selected_providers:
            for bm in selected_models:
                run_targets.append(
                    {
                        "provider": pn,
                        "benchmark_model": bm,
                        "provider_model": resolve_provider_model(
                            models_cfg, bm, pn
                        ),
                    }
                )
    elif run_matrix_path and run_matrix_path.exists():
        from cli.main import parse_run_matrix_config

        run_targets = parse_run_matrix_config(run_matrix_path, models_cfg)
    else:
        raise RuntimeError("Provide --providers/--models or a --config run matrix")

    sequence_files = _find_sequence_files(args)

    scoring_cfg = (
        load_yaml(Path(args.scoring))
        if Path(args.scoring).exists()
        else {"judge_weight": 0.85, "efficiency_weight": 0.15}
    )
    efficiency_cfg = (
        load_yaml(Path(args.efficiency))
        if Path(args.efficiency).exists()
        else {
            "latency_ms": 8000,
            "cost_usd": 0.2,
            "tps": 50,
            "weight_latency": 0.4,
            "weight_cost": 0.4,
            "weight_tps": 0.2,
        }
    )

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    run_root = Path(args.out) / timestamp
    run_root.mkdir(parents=True, exist_ok=True)

    all_results: List[Dict[str, Any]] = []

    log(
        f"[longrun] {len(sequence_files)} sequence(s) × {len(run_targets)} target(s)",
        verbosity,
        "normal",
    )

    for seq_file in sequence_files:
        sequence = load_yaml(seq_file)
        seq_dir = seq_file.parent
        seq_id = sequence.get("id", seq_dir.name)

        for target in run_targets:
            pn = target["provider"]
            bm = target["benchmark_model"]
            pm = target["provider_model"]

            run_name = f"{pn}__{safe_id(bm)}"
            run_dir = run_root / seq_id / run_name
            run_dir.mkdir(parents=True, exist_ok=True)

            log(
                f"[longrun] sequence={seq_id} provider={pn} model={bm}",
                verbosity,
                "normal",
            )

            pricing = models_cfg.get("models", {}).get(bm, {}).get("pricing")
            if not pricing:
                raise RuntimeError(f"Missing pricing for benchmark model: {bm}")

            result = _run_sequence(
                sequence,
                seq_dir,
                pn,
                bm,
                pm,
                run_dir,
                args,
                judge_cfg,
                scoring_cfg,
                efficiency_cfg,
                pricing,
                verbosity,
            )
            all_results.append(result)

            # Flush after every sequence: a multi-day run must not lose
            # completed records to a late crash, and partial tables read this.
            with open(run_root / "results.json", "w", encoding="utf-8") as f:
                json.dump({"results": all_results}, f, indent=2)

            agg = result.get("aggregate", {})
            log(
                f"[longrun] completed sequence={seq_id} provider={pn} "
                f"pass={agg.get('passed', 0)}/{agg.get('total_turns', 0)} "
                f"sum_score={agg.get('sum_final_score', 0)}",
                verbosity,
                "normal",
            )

    out_path = run_root / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"results": all_results}, f, indent=2)

    log(f"[longrun] wrote results to {out_path}", verbosity, "normal")
    total_runs = len(all_results)
    failed = [r for r in all_results if r.get("error") or r["aggregate"]["passed"] == 0]
    if failed:
        print(f"FAILED {len(failed)}/{total_runs} sequence(s). Results: {out_path}")
        sys.exit(1)
    print(f"OK {total_runs}/{total_runs} sequence(s). Results: {out_path}")


if __name__ == "__main__":
    main()

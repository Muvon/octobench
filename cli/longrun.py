"""Multi-turn long-run benchmark runner.

Runs a sequence of related tasks (one per commit) in a single agent session,
mimicking continuous user turns. The agent's source changes persist across
turns; validation checks out only the gold test files per turn.

With OCTOBENCH_FRESH_SESSIONS=1 every turn is a new agent session in the same
workspace instead, the way an autonomous agent meets one repository task after
another: only the working tree and what the client itself persisted (octomind's
learned memory) carry between turns. That is the setup a memory on/off
comparison needs.

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
import shlex
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from cli.main import (
    clean_workspace,
    compute_provider_result_cost,
    default_judge_cfg,
    diff_snapshots,
    enforce_clean_bench,
    ensure_workspace,
    install_guardrails,
    seal_network,
    unseal_network,
    load_yaml,
    log,
    make_executor,
    parse_providers,
    parse_selected_models,
    probe_provider_health,
    resolve_provider_model,
    run_case_script,
    safe_id,
    snapshot_files,
    write_text,
)
from judges.llm_judge import run_judge
from providers.base import ProviderRunResult
from providers.factory import get_provider
from runners.executor import Executor
from scoring.aggregate import (
    TOKEN_SEMANTICS,
    compute_efficiency_score,
    compute_final_score,
)


# Ceiling on one turn's gold-test run. An agent change can make a gold test
# loop forever; with no bound, that single validate ate the rest of a 10h
# sequence cap and lost every scored turn. Real validates run median 1s, max
# 87s (130 turns), so this never truncates a legitimate run. Enforced by
# `timeout` inside the container: killing the `docker exec` client alone
# leaves the test running into later turns.
VALIDATE_TIMEOUT_S = 1800

# A finished octomind session hands its transcript to a detached `octomind
# distill` child. In fresh-session mode the next turn must not start before it
# has stored what it learned, or the memory arm is measured without its memory.
# Extraction is a few supervisor calls; this bound only stops a hung child from
# stalling the sequence.
LEARNING_SETTLE_TIMEOUT_S = 600
LEARNING_SETTLE_POLL_S = 5


def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _build_turn_prompt(system_prompt: str, instruction: str, is_first_turn: bool) -> str:
    if is_first_turn:
        return f"System:\n{system_prompt}\n\nInstruction:\n{instruction}\n"
    return f"{instruction}\n"


def _unscored_turn_errors(turns: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    unscored = 0
    for idx, turn in enumerate(turns):
        if "unscored" in turn and not isinstance(turn["unscored"], bool):
            errors.append(f"turn {idx + 1}: unscored must be true or false")
            continue
        if turn.get("unscored") is not True:
            continue
        unscored += 1
        reason = turn.get("unscored_reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"turn {idx + 1}: unscored_reason is required when unscored")

    if unscored > 2:
        errors.append(f"has {unscored} unscored turns (maximum 2)")
    ratio_limit = len(turns) // 5
    if unscored > ratio_limit:
        errors.append(
            f"has {unscored} unscored turns (maximum floor({len(turns)}/5)={ratio_limit})"
        )
    return errors


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
    script += f"timeout -k 30 {VALIDATE_TIMEOUT_S} bash -c {shlex.quote(test_command)}\n"
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
    env.update(executor.harness_git_env())
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


# Substrings that mean the account cannot pay for the call. Retrying, or moving
# to the next turn, cannot clear any of them.
_BILLING_MARKERS = (
    "insufficient credits",
    "insufficient_quota",
    "exceeded your current quota",
    "billing",
    "payment required",
)


def _is_billing_failure(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in _BILLING_MARKERS)


def _restore_dependency(
    executor: Executor,
    repo_url: str,
    gold_sha: str,
    test_paths: List[str],
    turn_number: int,
    verbosity: str,
) -> bool:
    """Apply one failed predecessor's gold source diff to the workspace.

    Returns False when the gold diff cannot be applied — the agent's own later
    edits can conflict with it. The workspace is left untouched in that case
    (the script hard-resets), so the turn still runs, just without the
    predecessor's work, which is how the bench behaved before restoration
    existed. `restore_failed_dependencies` on the turn record marks it.
    """
    paths_arg = "\n".join(test_paths)
    script = (
        "set -euo pipefail\n"
        "git add -A\n"
        "git diff --cached --quiet || "
        "git -c user.email=bench@octobench -c user.name=octobench "
        f"commit -qm 'turn {turn_number} agent checkpoint'\n"
        f"git remote add origin {repo_url} 2>/dev/null || true\n"
        f"git fetch -q --depth 2 origin {gold_sha}\n"
        'ex=(":(exclude,icase)*changelog*" ":(exclude)*.md")\n'
        "while IFS= read -r t; do\n"
        '  [[ -n "$t" ]] && ex+=(":(exclude)$t")\n'
        "done <<< \"$TEST_PATHS\"\n"
        f"git diff --binary '{gold_sha}^1' '{gold_sha}' -- . \"${{ex[@]}}\" "
        "> /tmp/gold.patch\n"
        "if git apply --index /tmp/gold.patch 2>/dev/null \\\n"
        "   || git apply --3way --index /tmp/gold.patch; then\n"
        "  git -c user.email=bench@octobench -c user.name=octobench "
        f"commit -qm 'turn {turn_number} dependency gold' 2>/dev/null || true\n"
        "else\n"
        "  git reset -q --hard HEAD\n"
        "  grep '^+++ b/' /tmp/gold.patch | sed 's|^+++ b/||' | "
        "while IFS= read -r f; do\n"
        '    git ls-files --error-unmatch "$f" >/dev/null 2>&1 || rm -f "$f"\n'
        "  done\n"
        "  exit 1\n"
        "fi\n"
        "git remote remove origin 2>/dev/null || true\n"
    )

    log(
        f"[longrun] restore failed dependency turn={turn_number} "
        f"gold={gold_sha[:12]}",
        verbosity,
        "normal",
    )
    res = executor.run(
        ["bash", "-c", script],
        env_overrides={"TEST_PATHS": paths_arg, **executor.harness_git_env()},
    )
    if res.exit_code != 0:
        details = (res.stderr or "").strip() or (res.stdout or "").strip()
        log(
            f"[longrun] RESTORE-FAILED turn={turn_number} (turn runs unrestored)"
            + (f": {details[-300:]}" if details else ""),
            verbosity,
            "normal",
        )
        return False
    return True


def _settle_client_learning(executor: Executor, verbosity: str) -> Dict[str, Any]:
    """Wait for detached learning children to exit, then count stored memories.

    Returns how long the wait took, whether it timed out, and the hot learning
    records per memory type under the client's state dir.
    """
    # The process pattern is assembled at runtime so this script's own command
    # line never matches it.
    script = (
        "p=dist; p=\"${p}ill\"\n"
        f"deadline=$(( $(date +%s) + {LEARNING_SETTLE_TIMEOUT_S} ))\n"
        "start=$(date +%s); timed_out=0\n"
        "while :; do\n"
        "  busy=0\n"
        "  for f in /proc/[0-9]*/cmdline; do\n"
        "    c=$(tr '\\0' ' ' < \"$f\" 2>/dev/null) || continue\n"
        "    case \"$c\" in *\"octomind $p\"*) busy=1; break ;; esac\n"
        "  done\n"
        "  [ \"$busy\" = 0 ] && break\n"
        "  [ \"$(date +%s)\" -ge \"$deadline\" ] && { timed_out=1; break; }\n"
        f"  sleep {LEARNING_SETTLE_POLL_S}\n"
        "done\n"
        "echo \"waited_s=$(( $(date +%s) - start )) timed_out=$timed_out\"\n"
        "root=\"${OCTOMIND_DATA_DIR:-/root/.local/share/octomind}/learning\"\n"
        "[ -d \"$root\" ] && find \"$root\" -name '*.md' -not -path '*/.archive/*' "
        "-exec sed -n 's/^memory_type: *//p' {} + | sort | uniq -c\n"
        "exit 0\n"
    )
    res = executor.run(["bash", "-c", script])
    settled: Dict[str, Any] = {"waited_s": None, "timed_out": None, "records": {}}
    for line in (res.stdout or "").splitlines():
        parts = line.split()
        if line.startswith("waited_s="):
            fields = dict(part.split("=", 1) for part in parts)
            settled["waited_s"] = int(fields["waited_s"])
            settled["timed_out"] = fields["timed_out"] == "1"
        elif len(parts) == 2 and parts[0].isdigit():
            settled["records"][parts[1]] = int(parts[0])
    log(
        f"[longrun] learning settled in {settled['waited_s']}s "
        f"timed_out={settled['timed_out']} records={settled['records']}",
        verbosity,
        "normal",
    )
    return settled


def _synthetic_turn_result(
    turn_number: int,
    turn: Dict[str, Any],
    status: str,
    session_mode: str,
    elapsed_ms: int,
    provider_result: Optional[ProviderRunResult],
    pricing: Dict,
    efficiency_cfg: Dict,
    scoring_cfg: Dict,
) -> Dict[str, Any]:
    killed = status == "killed_by_sequence_cap"
    if provider_result is None:
        token_count = 0
        tokens = {
            "semantics": TOKEN_SEMANTICS,
            "input": token_count,
            "cached_input": token_count,
            "output": token_count,
            "reasoning": token_count,
            "aux_input": token_count,
            "aux_output": token_count,
            "total": token_count,
        }
        cost_usd: Optional[float] = 0.0
        session_id = None
        stdout = ""
    else:
        aux_tokens = (provider_result.aux_input_tokens or 0) + (
            provider_result.aux_output_tokens or 0
        )
        total_tokens = (
            provider_result.total_tokens + aux_tokens
            if provider_result.total_tokens is not None
            else None
        )
        tokens = {
            "semantics": TOKEN_SEMANTICS,
            "input": provider_result.input_tokens,
            "cached_input": provider_result.cached_input_tokens,
            "output": provider_result.output_tokens,
            "reasoning": provider_result.reasoning_tokens,
            "aux_input": provider_result.aux_input_tokens,
            "aux_output": provider_result.aux_output_tokens,
            "total": total_tokens,
        }
        cost_usd = compute_provider_result_cost(provider_result, pricing)
        elapsed_ms = provider_result.elapsed_ms
        session_id = provider_result.session_id
        stdout = (provider_result.stdout or "")[-2000:]

    if killed and provider_result is not None:
        efficiency = compute_efficiency_score(elapsed_ms, cost_usd, efficiency_cfg)
        raw_final_score = compute_final_score(0.0, efficiency, scoring_cfg)
        penalty = float(scoring_cfg.get("validation_fail_penalty", 25.0))
        final_score = round(max(0.0, raw_final_score - penalty), 2)
    else:
        efficiency = None
        raw_final_score = 0
        final_score = 0
    return {
        "turn": turn_number,
        "name": turn.get("name", f"turn_{turn_number}"),
        "instruction": turn.get("instruction", ""),
        "status": status,
        "restored_dependencies": [],
        "restore_failed_dependencies": [],
        "session_mode": session_mode,
        "client_learning": None,
        "provider": {
            "exit_code": 124 if killed else None,
            "elapsed_ms": elapsed_ms,
            "session_id": session_id,
            "stdout": stdout,
        },
        "tokens": tokens,
        "cost_usd": cost_usd,
        "validation": {"exit_code": None, "passed": False},
        "judge": None,
        "scoring": {
            "efficiency_score": efficiency,
            "raw_final_score": raw_final_score,
            "final_score": final_score,
            "validation_failed": True,
        },
    }


def _unscored_turn_result(
    turn_number: int,
    turn: Dict[str, Any],
    session_mode: str,
) -> Dict[str, Any]:
    unknown_tokens = {
        "semantics": TOKEN_SEMANTICS,
        "input": None,
        "cached_input": None,
        "output": None,
        "reasoning": None,
        "aux_input": None,
        "aux_output": None,
        "total": None,
    }
    return {
        "turn": turn_number,
        "name": turn.get("name", f"turn_{turn_number}"),
        "instruction": turn.get("instruction", ""),
        "status": "unscored",
        "unscored_reason": turn["unscored_reason"],
        "restored_dependencies": [],
        "restore_failed_dependencies": [],
        "session_mode": session_mode,
        "client_learning": None,
        "provider": {
            "exit_code": None,
            "elapsed_ms": None,
            "session_id": None,
            "stdout": "",
        },
        "tokens": unknown_tokens,
        "cost_usd": None,
        "validation": {"exit_code": None, "passed": None},
        "judge": None,
        "scoring": {
            "efficiency_score": None,
            "raw_final_score": None,
            "final_score": None,
            "validation_failed": None,
        },
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
    reasoning_effort: Optional[str],
    verbosity: str,
) -> Dict[str, Any]:
    """Run one full multi-turn sequence for a single provider+model."""
    seq_id = sequence.get("id", sequence_dir.name)
    system_prompt = sequence.get("system_prompt", "")
    turns = sequence.get("turns", [])
    unscored_errors = _unscored_turn_errors(turns)
    if unscored_errors:
        raise ValueError(f"{seq_id}: invalid unscored turns: {'; '.join(unscored_errors)}")
    max_turns = getattr(args, "max_turns", None)
    if max_turns:
        turns = turns[:max_turns]
    repo_url = sequence.get("meta", {}).get("repo", "")
    repo_root = Path.cwd().resolve()
    repo_config = Path(
        os.environ.get(
            "OCTOBENCH_OCTOMIND_CONFIG",
            str(repo_root / "configs" / "octomind" / "octomind.toml"),
        )
    )

    provider_impl = get_provider(provider_name)
    workdir = ensure_workspace(sequence_dir, run_dir)
    workdir_abs = workdir.resolve()
    executor = make_executor(
        args, workdir_abs, sequence_dir, repo_config, seq_id, provider_name
    )

    turn_results: List[Dict[str, Any]] = []
    restored_dependency_turns = set()
    session_id: Optional[str] = None
    has_run_agent = False
    fresh_sessions = os.environ.get("OCTOBENCH_FRESH_SESSIONS") == "1"
    session_mode = "fresh" if fresh_sessions else "resumed"
    setup_log: Optional[Dict[str, Any]] = None
    in_flight_turn: Optional[int] = None
    provider_started_at: Optional[float] = None
    in_flight_provider_result: Optional[ProviderRunResult] = None
    sequence_timed_out = False
    # Stable session name across all turns — octomind uses --name as the
    # session identifier, so it must not change between turns. Fresh-session
    # mode suffixes it per turn instead and never resumes.
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
            in_flight_turn = idx
            provider_started_at = None
            in_flight_provider_result = None
            turn_name = turn.get("name", f"turn_{idx + 1}")
            instruction = turn.get("instruction", "")
            gold_sha = turn.get("gold_sha", "")
            test_paths = turn.get("test_paths", [])
            test_command = turn.get("test_command", "")
            log(
                f"[longrun] turn {idx + 1}/{len(turns)}: {turn_name}",
                verbosity,
                "normal",
            )

            restored_dependencies: List[int] = []
            restore_failed_dependencies: List[int] = []
            for dependency_turn in turn.get("depends_on", []):
                dependency_idx = dependency_turn - 1
                dependency_result = turn_results[dependency_idx]
                if (
                    dependency_result["validation"]["passed"]
                    or dependency_turn in restored_dependency_turns
                ):
                    continue
                dependency = turns[dependency_idx]
                if _restore_dependency(
                    executor,
                    repo_url,
                    dependency.get("gold_sha", ""),
                    dependency.get("test_paths", []),
                    dependency_turn,
                    verbosity,
                ):
                    restored_dependency_turns.add(dependency_turn)
                    restored_dependencies.append(dependency_turn)
                else:
                    restore_failed_dependencies.append(dependency_turn)

            if turn.get("unscored") is True:
                if not _restore_dependency(
                    executor,
                    repo_url,
                    gold_sha,
                    test_paths,
                    idx + 1,
                    verbosity,
                ):
                    raise RuntimeError(
                        f"cannot apply gold source for unscored turn {idx + 1}: {turn_name}"
                    )
                restored_dependency_turns.add(idx + 1)
                turn_results.append(_unscored_turn_result(idx + 1, turn, session_mode))
                in_flight_turn = None
                log(
                    f"[longrun] turn {idx + 1} unscored: {turn['unscored_reason']}",
                    verbosity,
                    "normal",
                )
                continue

            # A fresh session has not seen the sequence's system prompt yet.
            prompt = _build_turn_prompt(
                system_prompt, instruction, not has_run_agent or fresh_sessions
            )
            install_guardrails(executor)
            sealed = os.environ.get("OCTOBENCH_SEAL_NETWORK") == "1"
            if sealed:
                seal_network(executor)
            before = snapshot_files(executor.workspace_host_path())

            turn_session = (
                f"{session_name}-t{idx + 1}" if fresh_sessions else session_name
            )

            provider_interrupted = False
            executor.begin_provider_call()
            try:
                provider_started_at = time.monotonic()
                in_flight_provider_result = provider_impl.run_task(
                    prompt=prompt,
                    workdir=executor.container_workspace(),
                    provider_model=provider_model,
                    session_name=turn_session,
                    executor=executor,
                    resume_session_id=None if fresh_sessions else session_id,
                    reasoning_effort=reasoning_effort,
                )
            finally:
                provider_interrupted = executor.end_provider_call()
                # _validate_turn fetches gold tests from the same hosts.
                if sealed:
                    unseal_network(executor)
            provider_result = in_flight_provider_result
            has_run_agent = True
            session_id = provider_result.session_id or session_id

            # Written before the cap check: a killed turn's partial trace is the
            # evidence for what ran into the cap (a client stuck in a loop).
            logs_dir = run_dir / "turns" / f"turn_{idx + 1}" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            write_text(logs_dir / "provider.stdout.log", provider_result.stdout or "")
            write_text(logs_dir / "provider.stderr.log", provider_result.stderr or "")
            write_text(logs_dir / "provider.raw.jsonl", provider_result.raw_output or "")

            if provider_interrupted:
                sequence_timed_out = True
                turn_results.append(
                    _synthetic_turn_result(
                        idx + 1,
                        turn,
                        "killed_by_sequence_cap",
                        session_mode,
                        provider_result.elapsed_ms,
                        provider_result,
                        pricing,
                        efficiency_cfg,
                        scoring_cfg,
                    )
                )
                in_flight_turn = None
                break

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
                # An exhausted account does not recover by trying the next turn:
                # every remaining one fails the same way in seconds and records as
                # a model failure. Stop the sequence so the run is short and
                # obviously broken instead of long and quietly wrong.
                if _is_billing_failure(err_tail):
                    raise RuntimeError(
                        f"provider billing failure on turn {idx + 1}, aborting sequence: "
                        f"{err_tail[:200]}"
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
            # The distill child started when the agent exited and has run during
            # validation; wait out the rest before the next turn recalls.
            client_learning = (
                _settle_client_learning(executor, verbosity) if fresh_sessions else None
            )

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

            aux_tokens = (provider_result.aux_input_tokens or 0) + (
                provider_result.aux_output_tokens or 0
            )
            tokens_total = (
                provider_result.total_tokens + aux_tokens
                if provider_result.total_tokens is not None
                else None
            )
            cost_usd = compute_provider_result_cost(provider_result, pricing)

            efficiency = compute_efficiency_score(
                provider_result.elapsed_ms, cost_usd, efficiency_cfg
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
                    "status": "completed",
                    "restored_dependencies": restored_dependencies,
                    "restore_failed_dependencies": restore_failed_dependencies,
                    "session_mode": session_mode,
                    "client_learning": client_learning,
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
                        "aux_input": provider_result.aux_input_tokens,
                        "aux_output": provider_result.aux_output_tokens,
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
            in_flight_turn = None
            provider_started_at = None
            verdict = "PASS" if not validation_failed else "FAIL"
            log(
                f"[longrun] turn {idx + 1} done: validate={verdict} "
                f"score={final_score}",
                verbosity,
                "normal",
            )

    except SystemExit as exc:
        if exc.code != 124:
            raise
        sequence_timed_out = True
        if in_flight_turn is not None and len(turn_results) == in_flight_turn:
            elapsed_ms = (
                in_flight_provider_result.elapsed_ms
                if in_flight_provider_result is not None
                else int((time.monotonic() - provider_started_at) * 1000)
                if provider_started_at is not None
                else 0
            )
            turn_results.append(
                _synthetic_turn_result(
                    in_flight_turn + 1,
                    turns[in_flight_turn],
                    "killed_by_sequence_cap",
                    session_mode,
                    elapsed_ms,
                    in_flight_provider_result,
                    pricing,
                    efficiency_cfg,
                    scoring_cfg,
                )
            )
    finally:
        # A sequence keeps its checkout for all its turns, so it can only be
        # dropped here. Rust/C++ build trees reach tens of GB each; without this
        # a 20-sequence campaign needs more disk than the box has. Turn logs,
        # diffs and scores live under run_dir/turns and are unaffected.
        clean_workspace(executor, workdir_abs, seq_id, verbosity)
        executor.close()

    if sequence_timed_out:
        for idx in range(len(turn_results), len(turns)):
            if turns[idx].get("unscored") is True:
                turn_results.append(
                    _unscored_turn_result(idx + 1, turns[idx], session_mode)
                )
            else:
                turn_results.append(
                    _synthetic_turn_result(
                        idx + 1,
                        turns[idx],
                        "not_run",
                        session_mode,
                        0,
                        None,
                        pricing,
                        efficiency_cfg,
                        scoring_cfg,
                    )
                )

    # Aggregate sequence-level metrics.
    scored_results = [turn for turn in turn_results if turn["status"] != "unscored"]
    total_turns = len(scored_results)
    unscored = len(turn_results) - total_turns
    passed = sum(
        1
        for turn in scored_results
        if turn["status"] == "completed" and turn["validation"]["passed"]
    )
    total_cost = sum(
        turn["cost_usd"]
        for turn in scored_results
        if turn["cost_usd"] is not None
    )
    total_tokens = sum(
        turn["tokens"]["total"]
        for turn in scored_results
        if turn["tokens"]["total"] is not None
    )
    # Each turn is valued separately; the sequence's score is the SUM of its
    # turn scores (avg kept for cross-length comparability).
    sum_score = sum(t["scoring"]["final_score"] for t in scored_results)
    avg_score = sum_score / total_turns if total_turns else 0

    result = {
        "sequence_id": seq_id,
        "provider": provider_name,
        "benchmark_model": benchmark_model,
        "provider_model": provider_model,
        "setup": {
            "exit_code": setup_log["exit_code"] if setup_log is not None else None,
        },
        "turns": turn_results,
        "aggregate": {
            "total_turns": total_turns,
            "unscored": unscored,
            "passed": passed,
            "pass_rate": round(passed / total_turns, 4) if total_turns else 0,
            "sum_final_score": round(sum_score, 2),
            "avg_final_score": round(avg_score, 2),
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
        },
    }
    if sequence_timed_out:
        result["error"] = "sequence_timeout"
    return result


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

        case_errs.extend(_unscored_turn_errors(turns))

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
    # bench.sh caps each sequence with `timeout`, which sends SIGTERM, and
    # Python's default SIGTERM exit skips `finally`: a capped sequence leaked its
    # workspace (54G for duckdb, enough to trip bench.sh's disk floor) and its
    # container. Exiting via SystemExit runs the cleanup; 124 keeps timeout's code.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(124))
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

    enforce_clean_bench(sorted({t["provider"] for t in run_targets}), verbosity)

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
            reasoning_effort = models_cfg["models"][bm].get("reasoning_effort")

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
                reasoning_effort,
                verbosity,
            )
            if result.get("error") == "sequence_timeout":
                healthy, detail = probe_provider_health(
                    repo_root,
                    models_cfg,
                    bm,
                    run_dir / "provider-health",
                )
                if not healthy:
                    result["error"] = "provider_unavailable"
                    result["provider_unavailable"] = detail
                    unavailable_path = run_root / "results.provider_unavailable.json"
                    with open(unavailable_path, "w", encoding="utf-8") as f:
                        json.dump({"results": [result]}, f, indent=2)
                    log(
                        f"[longrun] PROVIDER-UNAVAILABLE sequence={seq_id} detail={detail}",
                        verbosity,
                        "normal",
                    )
                    raise SystemExit(124)

            all_results.append(result)

            # Flush after every sequence: a multi-day run must not lose
            # completed records to a late crash, and partial tables read this.
            with open(run_root / "results.json", "w", encoding="utf-8") as f:
                json.dump({"results": all_results}, f, indent=2)

            if result.get("error") == "sequence_timeout":
                completed = sum(
                    turn.get("status") == "completed"
                    for turn in result["turns"]
                )
                planned = result["aggregate"]["total_turns"]
                log(
                    f"[longrun] SEQUENCE-CAP sequence={seq_id} "
                    f"completed={completed}/{planned}",
                    verbosity,
                    "normal",
                )
                raise SystemExit(124)

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

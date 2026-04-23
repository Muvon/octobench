from __future__ import annotations

import argparse
import difflib
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml

from judges.llm_judge import run_judge
from providers.factory import available_providers, get_provider
from scoring.aggregate import compute_cost, compute_efficiency_score, compute_final_score


def _load_gitignore_rules(workdir: Path) -> list[tuple[Path, str, bool, bool]]:
    """
    Return parsed gitignore rules as tuples:
    (base_dir, pattern, negated, dir_only)
    """
    rules: list[tuple[Path, str, bool, bool]] = []
    for gitignore in workdir.rglob(".gitignore"):
        base_dir = gitignore.parent
        try:
            lines = gitignore.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            negated = line.startswith("!")
            pattern = line[1:] if negated else line
            pattern = pattern.strip()
            if not pattern:
                continue
            dir_only = pattern.endswith("/")
            if dir_only:
                pattern = pattern[:-1]
            rules.append((base_dir, pattern, negated, dir_only))
    return rules


def _match_gitignore_pattern(rel_from_base: str, name: str, pattern: str, dir_only: bool) -> bool:
    rel = rel_from_base.replace("\\", "/")
    pat = pattern.replace("\\", "/")
    if pat.startswith("/"):
        anchored = pat.lstrip("/")
        if rel == anchored or rel.startswith(anchored + "/"):
            return True
        return False

    # No slash: match any path segment name.
    if "/" not in pat:
        if fnmatch.fnmatchcase(name, pat):
            return True
        parts = rel.split("/")
        return any(fnmatch.fnmatchcase(p, pat) for p in parts)

    # Path pattern relative to the .gitignore base directory.
    if fnmatch.fnmatchcase(rel, pat):
        return True
    # Directory rule should match descendants too.
    if dir_only and (rel == pat or rel.startswith(pat + "/")):
        return True
    return False


def _is_gitignored(path: Path, workdir: Path, rules: list[tuple[Path, str, bool, bool]]) -> bool:
    ignored = False
    name = path.name
    for base_dir, pattern, negated, dir_only in rules:
        try:
            rel_from_base = str(path.relative_to(base_dir))
        except Exception:
            continue
        if _match_gitignore_pattern(rel_from_base, name, pattern, dir_only):
            ignored = not negated
    return ignored


def snapshot_files(workdir: Path) -> Dict[str, Dict]:
    files = {}
    rules = _load_gitignore_rules(workdir)
    for path in workdir.rglob("*"):
        if path.is_file():
            rel = str(path.relative_to(workdir))
            if (
                rel.startswith("_provider_output_")
                or rel.startswith("_prompt_")
                or rel.startswith("_output_")
            ):
                continue
            if _is_gitignored(path, workdir, rules):
                continue
            try:
                data = path.read_bytes()
            except Exception:
                continue
            content = None
            try:
                text = data.decode("utf-8")
                if len(text) <= 4000:
                    content = text
            except Exception:
                content = None
            files[rel] = {
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "content": content,
            }
    return files


def diff_snapshots(before: Dict[str, Dict], after: Dict[str, Dict]) -> Dict:
    before_set = set(before.keys())
    after_set = set(after.keys())
    added = sorted(after_set - before_set)
    deleted = sorted(before_set - after_set)
    modified = sorted(
        k for k in (before_set & after_set) if before[k]["sha256"] != after[k]["sha256"]
    )
    return {"added": added, "deleted": deleted, "modified": modified}


def build_evidence(before: Dict[str, Dict], after: Dict[str, Dict], diff: Dict) -> str:
    lines = []
    lines.append("CHANGES")
    lines.append(f"added: {len(diff['added'])}")
    lines.append(f"deleted: {len(diff['deleted'])}")
    lines.append(f"modified: {len(diff['modified'])}")
    for label in ["added", "deleted", "modified"]:
        if diff[label]:
            lines.append(f"{label}:")
            lines.extend([f"- {p}" for p in diff[label]])

    for rel in diff["modified"]:
        before_c = before.get(rel, {}).get("content")
        after_c = after.get(rel, {}).get("content")
        if before_c is None or after_c is None:
            continue
        diff_lines = difflib.unified_diff(
            before_c.splitlines(),
            after_c.splitlines(),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            lineterm="",
        )
        lines.append("\n".join(diff_lines))

    return "\n".join(lines)


def load_yaml(path: Path) -> Dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content or "", encoding="utf-8")


def find_case_files(root: Path) -> List[Path]:
    return list(root.rglob("case.yaml"))


def run_script(
    script_path: Path,
    workdir: Path,
    env: Dict[str, str] | None = None,
    verbosity: str = "normal",
) -> Dict:
    script_path = script_path.resolve()
    script_name = script_path.name
    if not script_path.exists():
        return {"exit_code": 0, "stdout": "", "stderr": "", "elapsed_ms": 0}
    log(f"[octobench] script={script_name} start cwd={workdir}", verbosity, "normal")
    start = time.time()
    proc = subprocess.Popen(
        ["bash", str(script_path)],
        cwd=str(workdir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env={**os.environ, **(env or {})},
    )

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []

    def pump(stream, target: List[str], stream_label: str) -> None:
        for raw in iter(stream.readline, ""):
            target.append(raw)
            if verbosity != "quiet":
                line = raw.rstrip("\n")
                if line:
                    log(
                        f"[octobench] script={script_name} {stream_label}: {line}",
                        verbosity,
                        "normal",
                    )
        stream.close()

    t_out = threading.Thread(target=pump, args=(proc.stdout, stdout_lines, "stdout"), daemon=True)
    t_err = threading.Thread(target=pump, args=(proc.stderr, stderr_lines, "stderr"), daemon=True)
    t_out.start()
    t_err.start()
    return_code = proc.wait()
    t_out.join()
    t_err.join()

    elapsed_ms = int((time.time() - start) * 1000)
    log(
        f"[octobench] script={script_name} end exit={return_code} elapsed_ms={elapsed_ms}",
        verbosity,
        "normal",
    )
    return {
        "exit_code": return_code,
        "stdout": "".join(stdout_lines),
        "stderr": "".join(stderr_lines),
        "elapsed_ms": elapsed_ms,
    }


def ensure_workspace(case_dir: Path, run_dir: Path) -> Path:
    workdir = run_dir / "workspace"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


def build_task_prompt(case: Dict) -> str:
    return (
        f"System:\n{case.get('system_prompt', '')}\n\nInstruction:\n{case.get('instruction', '')}\n"
    )


def parse_selected_models(models_cfg: Dict, models_arg: str | None) -> List[str]:
    available = list(models_cfg.get("models", {}).keys())
    if not models_arg:
        return available
    selected = [m.strip() for m in models_arg.split(",") if m.strip()]
    unknown = [m for m in selected if m not in models_cfg.get("models", {})]
    if unknown:
        raise RuntimeError(f"Unknown benchmark model(s): {', '.join(unknown)}")
    return selected


def parse_run_matrix_config(config_path: Path, models_cfg: Dict) -> List[Dict[str, str]]:
    data = load_yaml(config_path)
    runs: Any
    if isinstance(data, list):
        runs = data
    elif isinstance(data, dict):
        runs = data.get("runs")
    else:
        runs = None

    if not isinstance(runs, list) or not runs:
        raise RuntimeError(
            f"Invalid run matrix config at {config_path}: expected non-empty list in 'runs'"
        )

    known_providers = set(available_providers())
    known_models = set(models_cfg.get("models", {}).keys())
    run_targets: List[Dict[str, str]] = []

    for i, raw in enumerate(runs, start=1):
        if not isinstance(raw, dict):
            raise RuntimeError(
                f"Invalid run matrix entry #{i} in {config_path}: expected mapping/object"
            )

        provider = raw.get("provider")
        benchmark_model = raw.get("benchmark_model") or raw.get("model")
        provider_model = raw.get("provider_model")

        if not provider:
            raise RuntimeError(f"Invalid run matrix entry #{i}: missing required key 'provider'")
        provider = str(provider)
        if provider not in known_providers:
            raise RuntimeError(
                f"Invalid run matrix entry #{i}: unknown provider '{provider}'"
            )

        if not benchmark_model:
            raise RuntimeError(
                f"Invalid run matrix entry #{i}: missing required key 'model' "
                "(or 'benchmark_model')"
            )
        benchmark_model = str(benchmark_model)
        if benchmark_model not in known_models:
            raise RuntimeError(
                f"Invalid run matrix entry #{i}: unknown benchmark model '{benchmark_model}'"
            )

        if provider_model is None:
            provider_model = resolve_provider_model(models_cfg, benchmark_model, provider)
        else:
            provider_model = str(provider_model)

        run_targets.append(
            {
                "provider": provider,
                "benchmark_model": benchmark_model,
                "provider_model": provider_model,
            }
        )

    return run_targets


def resolve_provider_model(models_cfg: Dict, benchmark_model: str, provider: str) -> str:
    entry = models_cfg.get("models", {}).get(benchmark_model, {})
    providers = entry.get("providers", {})
    mapped = providers.get(provider)
    if mapped is None:
        raise RuntimeError(
            "Missing provider mapping for benchmark_model "
            f"'{benchmark_model}' and provider '{provider}'"
        )
    if isinstance(mapped, dict):
        model_id = mapped.get("id")
    else:
        model_id = mapped
    if not model_id:
        raise RuntimeError(
            "Invalid provider mapping for benchmark_model "
            f"'{benchmark_model}' and provider '{provider}'"
        )
    return str(model_id)


def safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)


def should_log(level: str, current: str) -> bool:
    rank = {"quiet": 0, "normal": 1, "debug": 2}
    return rank.get(current, 1) >= rank.get(level, 1)


def log(msg: str, verbosity: str, level: str = "normal") -> None:
    if should_log(level, verbosity):
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        print(f"[{ts}] {msg}", file=sys.stderr)


def parse_providers(arg: str | None) -> List[str]:
    all_known = set(available_providers())
    if not arg:
        return sorted(all_known)
    selected = [p.strip() for p in arg.split(",") if p.strip()]
    unknown = [p for p in selected if p not in all_known]
    if unknown:
        raise RuntimeError(f"Unknown provider(s): {', '.join(unknown)}")
    return selected


def default_judge_cfg(repo_root: Path) -> Dict:
    return {
        "name": "octomind_judge",
        "runner": "cli",
        "model": "openrouter:anthropic/claude-sonnet-4",
        "stdin_prompt": True,
        "command": ["octomind", "run", "judge", "--format=jsonl"],
        "json_events": True,
        "env": {
            "OCTOMIND_CONFIG_PATH": f"{repo_root}/configs/octomind/octomind.toml",
        },
        "response_format": "json",
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="python3 -m cli.main")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run benchmarks")
    run_p.add_argument("--cases", required=True)
    run_p.add_argument("--providers", default=None, help="Comma-separated providers")
    run_p.add_argument("--models", default=None, help="Comma-separated benchmark model keys")
    run_p.add_argument(
        "--config",
        default="configs/run-matrix.yaml",
        help=(
            "Path to run matrix config (explicit provider/model pairs). "
            "Used by default when --providers/--models are not set."
        ),
    )
    run_p.add_argument("--out", default="results")
    run_p.add_argument("--scoring", default="configs/scoring.yaml")
    run_p.add_argument("--efficiency", default="configs/efficiency.yaml")
    run_p.add_argument("--verbosity", choices=["quiet", "normal", "debug"], default="normal")

    args = parser.parse_args()

    if args.cmd != "run":
        return

    verbosity = args.verbosity
    repo_root = Path.cwd().resolve()
    cases_root = Path(args.cases)
    judge_cfg = default_judge_cfg(repo_root)
    models_path = repo_root / "configs" / "models.yaml"
    if not models_path.exists():
        raise RuntimeError(f"Missing required models config: {models_path}")
    models_cfg = load_yaml(models_path)
    use_run_matrix = False
    run_matrix_path = Path(args.config) if args.config else Path("configs/run-matrix.yaml")
    if args.providers is not None or args.models is not None:
        selected_models = parse_selected_models(models_cfg, args.models)
        selected_providers = parse_providers(args.providers)
        run_targets = []
        for provider_name in selected_providers:
            for benchmark_model in selected_models:
                run_targets.append(
                    {
                        "provider": provider_name,
                        "benchmark_model": benchmark_model,
                        "provider_model": resolve_provider_model(
                            models_cfg, benchmark_model, provider_name
                        ),
                    }
                )
    elif run_matrix_path.exists():
        use_run_matrix = True
        run_targets = parse_run_matrix_config(run_matrix_path, models_cfg)
    else:
        # Fallback behavior when no run-matrix config exists.
        selected_models = parse_selected_models(models_cfg, args.models)
        selected_providers = parse_providers(args.providers)
        run_targets = []
        for provider_name in selected_providers:
            for benchmark_model in selected_models:
                run_targets.append(
                    {
                        "provider": provider_name,
                        "benchmark_model": benchmark_model,
                        "provider_model": resolve_provider_model(
                            models_cfg, benchmark_model, provider_name
                        ),
                    }
                )

    selected_providers = sorted({t["provider"] for t in run_targets})

    scoring_cfg = (
        load_yaml(Path(args.scoring))
        if Path(args.scoring).exists()
        else {
            "judge_weight": 0.85,
            "efficiency_weight": 0.15,
        }
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

    case_files = find_case_files(cases_root)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    run_root = Path(args.out) / timestamp
    run_root.mkdir(parents=True, exist_ok=True)

    all_results = []

    provider_impls = {name: get_provider(name, repo_root) for name in selected_providers}

    if use_run_matrix:
        log(
            (
                f"[octobench] loaded {len(run_targets)} run target(s) from "
                f"{run_matrix_path}, cases from {cases_root}"
            ),
            verbosity,
            "normal",
        )
    else:
        log(
            (
                f"[octobench] loaded {len(selected_models)} model(s), "
                f"{len(selected_providers)} provider(s), cases from {cases_root}"
            ),
            verbosity,
            "normal",
        )

    for case_file in case_files:
        case = load_yaml(case_file)
        case_dir = case_file.parent
        case_id = case.get("id", case_dir.name)
        case_run_dir = run_root / case_id
        case_run_dir.mkdir(parents=True, exist_ok=True)
        log(f"[octobench] case={case_id}", verbosity, "normal")

        used_setup_names: dict[str, int] = {}
        for target in run_targets:
            provider_name = target["provider"]
            benchmark_model = target["benchmark_model"]
            provider_model = target["provider_model"]
            provider_impl = provider_impls[provider_name]

            setup_key = benchmark_model
            setup_base = f"{provider_name}__{safe_id(setup_key)}"
            setup_index = used_setup_names.get(setup_base, 0)
            used_setup_names[setup_base] = setup_index + 1
            setup_name = setup_base if setup_index == 0 else f"{setup_base}__{setup_index+1}"
            setup_run_dir = case_run_dir / setup_name
            setup_run_dir.mkdir(parents=True, exist_ok=True)
            logs_dir = setup_run_dir / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)

            log(
                (
                    f"[octobench] run provider={provider_name} "
                    f"benchmark_model={benchmark_model} "
                    f"provider_model={provider_model}"
                ),
                verbosity,
                "debug",
            )

            workdir = ensure_workspace(case_dir, setup_run_dir)
            workdir_abs = workdir.resolve()

            env = {
                "CASE_DIR": str(case_dir.resolve()),
                "WORKDIR": str(workdir_abs),
            }
            setup_log = run_script(case_dir / "setup.sh", workdir_abs, env=env, verbosity=verbosity)
            if setup_log["exit_code"] != 0:
                quality_log = run_script(
                    case_dir / "quality.sh", workdir_abs, env=env, verbosity=verbosity
                )
                validation_log = run_script(
                    case_dir / "validate.sh", workdir_abs, env=env, verbosity=verbosity
                )
                write_text(logs_dir / "setup.stdout.log", setup_log["stdout"])
                write_text(logs_dir / "setup.stderr.log", setup_log["stderr"])
                write_text(logs_dir / "quality.stdout.log", quality_log["stdout"])
                write_text(logs_dir / "quality.stderr.log", quality_log["stderr"])
                write_text(logs_dir / "validate.stdout.log", validation_log["stdout"])
                write_text(logs_dir / "validate.stderr.log", validation_log["stderr"])
                setup_err = (setup_log["stderr"] or "").strip()
                setup_out = (setup_log["stdout"] or "").strip()
                detail = setup_err if setup_err else setup_out
                if detail:
                    detail = detail[-1200:]
                    setup_failed_msg = f"setup failed (exit={setup_log['exit_code']}): {detail}"
                else:
                    setup_failed_msg = f"setup failed (exit={setup_log['exit_code']})"
                judge_payload = {
                    "task": "",
                    "prep_log": setup_log["stdout"] + setup_log["stderr"],
                    "quality_log": quality_log["stdout"] + quality_log["stderr"],
                    "validation_log": validation_log["stdout"] + validation_log["stderr"],
                    "evidence_log": "",
                }
                judge_meta = dict(judge_cfg)
                judge_meta["io_dir"] = str(logs_dir.resolve())
                judge_meta["repo_root"] = str(repo_root)
                judge_out = run_judge(judge_payload, judge_meta, str(workdir_abs))
                write_text(logs_dir / "judge.raw.log", str(judge_out.get("_judge_raw", "")))
                record = {
                    "case_id": case_id,
                    "setup": setup_name,
                    "provider": provider_name,
                    "model": benchmark_model,
                    "provider_model": provider_model,
                    "runner": "provider",
                    "result": {
                        "stdout": "",
                        "stderr": setup_failed_msg,
                        "exit_code": 1,
                        "elapsed_ms": 0,
                    },
                    "tokens": {
                        "input": None,
                        "cached_input": None,
                        "output": None,
                        "reasoning": None,
                        "total": None,
                    },
                    "cost_usd": None,
                    "scripts": {
                        "setup": setup_log,
                        "quality": quality_log,
                        "validate": validation_log,
                    },
                    "evidence": "",
                    "evidence_diff": "",
                    "provider_evidence": "",
                    "workdir": str(workdir_abs),
                    "judge": judge_out,
                    "scoring": {},
                }
                all_results.append(record)
                continue

            prompt = build_task_prompt(case)
            before = snapshot_files(workdir_abs)

            session_name = (
                f"ob-{safe_id(case_id)[:20]}-{provider_name[:8]}-"
                f"{safe_id(benchmark_model)[:12]}-{int(time.time())}"
            )
            provider_result = provider_impl.run_task(
                prompt=prompt,
                workdir=str(workdir_abs),
                provider_model=provider_model,
                session_name=session_name,
            )
            if provider_result.exit_code != 0:
                err_tail = (provider_result.stderr or "").strip() or (
                    provider_result.stdout or ""
                ).strip()
                if err_tail:
                    err_tail = err_tail[-1200:]
                raise RuntimeError(
                    f"Provider failed: case={case_id} provider={provider_name} "
                    f"model={benchmark_model} "
                    f"exit={provider_result.exit_code}"
                    + (f" details={err_tail}" if err_tail else "")
                )

            after = snapshot_files(workdir_abs)
            diff = diff_snapshots(before, after)
            evidence_log_diff = build_evidence(before, after, diff)
            provider_evidence = provider_impl.build_provider_evidence(provider_result)
            evidence_parts = []
            if provider_evidence:
                evidence_parts.append(
                    "<provider_evidence>\n"
                    + provider_evidence.strip()
                    + "\n</provider_evidence>"
                )
            if evidence_log_diff:
                evidence_parts.append(
                    "<evidence_diff>\n" + evidence_log_diff.strip() + "\n</evidence_diff>"
                )
            evidence_log = "\n\n".join(p for p in evidence_parts if p)

            quality_log = run_script(
                case_dir / "quality.sh", workdir_abs, env=env, verbosity=verbosity
            )
            validation_log = run_script(
                case_dir / "validate.sh", workdir_abs, env=env, verbosity=verbosity
            )
            write_text(logs_dir / "setup.stdout.log", setup_log["stdout"])
            write_text(logs_dir / "setup.stderr.log", setup_log["stderr"])
            write_text(logs_dir / "quality.stdout.log", quality_log["stdout"])
            write_text(logs_dir / "quality.stderr.log", quality_log["stderr"])
            write_text(logs_dir / "validate.stdout.log", validation_log["stdout"])
            write_text(logs_dir / "validate.stderr.log", validation_log["stderr"])
            write_text(logs_dir / "provider.stdout.log", provider_result.stdout or "")
            write_text(logs_dir / "provider.stderr.log", provider_result.stderr or "")

            judge_payload = {
                "task": prompt,
                "prep_log": setup_log["stdout"] + setup_log["stderr"],
                "quality_log": quality_log["stdout"] + quality_log["stderr"],
                "validation_log": validation_log["stdout"] + validation_log["stderr"],
                "evidence_log": evidence_log,
            }
            judge_meta = dict(judge_cfg)
            judge_meta["io_dir"] = str(logs_dir.resolve())
            judge_meta["repo_root"] = str(repo_root)
            judge_out = run_judge(judge_payload, judge_meta, str(workdir_abs))
            write_text(logs_dir / "judge.raw.log", str(judge_out.get("_judge_raw", "")))

            pricing = models_cfg.get("models", {}).get(benchmark_model, {}).get("pricing")
            if not pricing:
                raise RuntimeError(f"Missing pricing for benchmark model: {benchmark_model}")

            eval_cost = compute_cost(
                provider_result.input_tokens,
                provider_result.cached_input_tokens,
                provider_result.output_tokens,
                pricing,
            )

            record = {
                "case_id": case_id,
                "setup": setup_name,
                "provider": provider_name,
                "model": benchmark_model,
                "provider_model": provider_model,
                "runner": "provider",
                "result": {
                    "stdout": provider_result.stdout,
                    "stderr": provider_result.stderr,
                    "exit_code": provider_result.exit_code,
                    "elapsed_ms": provider_result.elapsed_ms,
                },
                "tokens": {
                    "input": provider_result.input_tokens,
                    "cached_input": provider_result.cached_input_tokens,
                    "output": provider_result.output_tokens,
                    "reasoning": provider_result.reasoning_tokens,
                    "total": provider_result.total_tokens,
                },
                "cost_usd": eval_cost,
                "scripts": {
                    "setup": setup_log,
                    "quality": quality_log,
                    "validate": validation_log,
                },
                "evidence": evidence_log,
                "evidence_diff": evidence_log_diff,
                "provider_evidence": provider_evidence,
                "workdir": str(workdir_abs),
                "judge": judge_out,
                "scoring": {},
            }
            all_results.append(record)
            log(
                (
                    f"[octobench] completed case={case_id} "
                    f"setup={setup_name} exit={provider_result.exit_code}"
                ),
                verbosity,
                "normal",
            )

    for case_id in {r["case_id"] for r in all_results}:
        case_rows = [r for r in all_results if r["case_id"] == case_id]
        for r in case_rows:
            judge_score = float(r["judge"].get("score", 0))
            efficiency = compute_efficiency_score(
                r["result"]["elapsed_ms"], r["tokens"]["total"], r.get("cost_usd"), efficiency_cfg
            )
            validation_failed = r["scripts"]["validate"]["exit_code"] != 0
            raw_final_score = compute_final_score(judge_score, efficiency, scoring_cfg)
            validation_fail_penalty = float(scoring_cfg.get("validation_fail_penalty", 25.0))
            penalty_applied = validation_fail_penalty if validation_failed else 0.0
            final_score = round(max(0.0, raw_final_score - penalty_applied), 2)
            r["scoring"].update(
                {
                    "efficiency_score": efficiency,
                    "raw_final_score": raw_final_score,
                    "validation_penalty": penalty_applied,
                    "final_score": final_score,
                    "validation_failed": validation_failed,
                    "judge_weight": scoring_cfg.get("judge_weight", 0.85),
                    "efficiency_weight": scoring_cfg.get("efficiency_weight", 0.15),
                }
            )

    total_runs = len(all_results)
    failed_runs = [
        r
        for r in all_results
        if (
            r["scripts"]["setup"]["exit_code"] != 0
            or r["result"]["exit_code"] != 0
            or r["scripts"]["validate"]["exit_code"] != 0
        )
    ]

    out_path = run_root / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"results": all_results}, f, indent=2)

    log(f"[octobench] wrote results to {out_path}", verbosity, "normal")
    if failed_runs:
        print(f"FAILED {len(failed_runs)}/{total_runs} run(s). Results: {out_path}")
        sys.exit(1)
    print(f"OK {total_runs}/{total_runs} run(s). Results: {out_path}")


if __name__ == "__main__":
    main()

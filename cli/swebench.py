from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

from cli.main import (
    build_task_prompt,
    default_judge_cfg,
    load_yaml,
    log,
    parse_run_matrix_config,
    safe_id,
    write_text,
)
from judges.llm_judge import run_judge
from providers.factory import get_provider
from runners.executor import DockerExecutor
from scoring.aggregate import compute_cost, compute_efficiency_score

# SWE-bench-Live: real, post-2024 GitHub issues, execution-verified, contamination-
# resistant. We run one instance through the SAME conceptual flow as local cases
# (task -> agent -> objective verify -> judge -> score), but the repo + test env
# live inside the instance's Docker image (at /testbed), so we run repo-in-image.
HF_ROWS = "https://datasets-server.huggingface.co/rows"
DATASET = "SWE-bench-Live/SWE-bench-Live"

SYSTEM_PROMPT = (
    "You are an autonomous software engineer working in the git repository at "
    "/testbed. Resolve the reported issue with the minimal necessary code change. "
    "Do NOT modify tests. When done, stop."
)


def fetch_rows(split: str, length: int = 100, offset: int = 0) -> List[Dict]:
    url = (
        f"{HF_ROWS}?dataset={urllib.parse.quote(DATASET)}"
        f"&config=default&split={split}&offset={offset}&length={length}"
    )
    # Snapshot cache: the dataset is frozen, but the HF rows endpoint has outages
    # (503s) that would otherwise fail every bench run. Refresh on success; fall
    # back to the last good snapshot on failure.
    cache = f"/home/box/work/muvon/octobench/.hf_rows_cache_{split}_{offset}_{length}.json"
    # The public HF endpoint occasionally drops the TLS connection mid-read; retry.
    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as resp:  # noqa: S310 (trusted HF endpoint)
                data = json.load(resp)
            rows = [r["row"] for r in data.get("rows", [])]
            try:
                with open(cache, "w") as f:
                    json.dump(rows, f)
            except OSError:
                pass
            return rows
        except Exception as e:  # transient TLS/EOF/5xx — back off and retry
            last_err = e
            if attempt < 3:
                time.sleep(1.5 * (attempt + 1))
    try:
        with open(cache) as f:
            rows = json.load(f)
        print(f"WARNING: HF fetch failed ({last_err}); using snapshot cache {cache}")
        return rows
    except OSError:
        pass
    raise RuntimeError(f"HF fetch failed for split '{split}': {last_err}")


def _as_list(value) -> List[str]:
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except Exception:
        return []


def select_instance(split: str, instance_id: Optional[str]) -> Dict:
    rows = fetch_rows(split, length=100)
    if not rows:
        raise RuntimeError(f"No rows returned for split '{split}'")
    if instance_id:
        for r in rows:
            if r.get("instance_id") == instance_id:
                return r
        raise RuntimeError(f"instance '{instance_id}' not found in split '{split}'")
    # Default: smallest instance (fewest tests) — fastest to prove the flow.
    rows.sort(key=lambda r: sum(len(_as_list(r.get(k))) for k in ("FAIL_TO_PASS", "PASS_TO_PASS")))
    return rows[0]


def instance_image(instance_id: str) -> str:
    # SWE-bench image-name sanitization: '__' -> '_1776_' (DockerHub: starryzhang).
    return f"starryzhang/sweb.eval.x86_64.{instance_id.replace('__', '_1776_')}:latest"


def derived_image(instance_id: str) -> str:
    return f"octobench-sweb:{safe_id(instance_id)}"


def build_derived_image(instance_id: str, repo_root: Path, verbosity: str) -> str:
    base = instance_image(instance_id)
    derived = derived_image(instance_id)
    if subprocess.run(["docker", "image", "inspect", derived], capture_output=True).returncode == 0:
        log(f"[swebench] derived image cached: {derived}", verbosity, "normal")
        return derived
    log(f"[swebench] building {derived} FROM {base} (amd64, emulated)...", verbosity, "normal")
    cmd = [
        "docker", "build", "--platform", "linux/amd64",
        "-f", str(repo_root / "docker" / "Dockerfile.swebench"),
        "--build-arg", f"BASE_IMAGE={base}",
        "-t", derived, str(repo_root / "docker"),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"derived image build failed:\n{proc.stderr[-2500:]}")
    return derived


_RESULT_RE = re.compile(r"^(PASSED|FAILED|ERROR|SKIPPED)\s+(\S+)", re.M)


def parse_test_results(output: str, fail_to_pass: List[str], pass_to_pass: List[str]) -> Dict:
    """Parse pytest -rA short-summary lines and check the SWE-bench gate."""
    status: Dict[str, str] = {}
    for m in _RESULT_RE.finditer(output):
        status[m.group(2)] = m.group(1)

    def passed(tid: str) -> bool:
        return status.get(tid) == "PASSED"

    f2p_ok = [t for t in fail_to_pass if passed(t)]
    p2p_ok = [t for t in pass_to_pass if passed(t)]
    resolved = len(f2p_ok) == len(fail_to_pass) and len(p2p_ok) == len(pass_to_pass)
    return {
        "resolved": resolved,
        "fail_to_pass": f"{len(f2p_ok)}/{len(fail_to_pass)}",
        "pass_to_pass": f"{len(p2p_ok)}/{len(pass_to_pass)}",
        "results_seen": len(status),
    }


def _run(executor: DockerExecutor, script: str, input_text: Optional[str] = None):
    return executor.run(["bash", "-lc", script], input_text=input_text)


def run_instance(instance: Dict, target: Dict, repo_root: Path, models_cfg: Dict,
                 judge_cfg: Dict, out_dir: Path, verbosity: str) -> Dict:
    instance_id = instance["instance_id"]
    provider_name = target["provider"]
    benchmark_model = target["benchmark_model"]
    provider_model = target["provider_model"]
    provider_impl = get_provider(provider_name)

    base_commit = instance["base_commit"]
    test_patch = instance.get("test_patch", "")
    test_cmds = _as_list(instance.get("test_cmds")) or ["pytest -rA"]
    fail_to_pass = _as_list(instance.get("FAIL_TO_PASS"))
    pass_to_pass = _as_list(instance.get("PASS_TO_PASS"))
    problem = instance.get("problem_statement", "")

    logs_dir = out_dir / safe_id(instance_id) / f"{provider_name}__{safe_id(benchmark_model)}"
    logs_dir.mkdir(parents=True, exist_ok=True)

    derived = build_derived_image(instance_id, repo_root, verbosity)
    repo_config = repo_root / "configs" / "octomind" / "octomind.toml"
    name = f"obsweb-{safe_id(instance_id)[:22]}-{provider_name[:6]}-{int(time.time() * 1000)}"
    executor = DockerExecutor(
        derived, repo_root, repo_root, repo_config, name,
        workdir="/testbed", platform="linux/amd64",
        mount_workspace=False, mount_case=False,
    )

    try:
        # Reset repo to base_commit, then apply the PR's test patch so the
        # FAIL_TO_PASS tests exist for verification.
        _run(executor, "git config --global --add safe.directory /testbed")
        _run(executor, f"cd /testbed && git reset --hard {base_commit} -q && git clean -fdq")
        if test_patch.strip():
            _run(executor, "cat > /tmp/test.patch", input_text=test_patch)
            ap = _run(executor, "cd /testbed && git apply -v /tmp/test.patch 2>&1 || "
                                "(patch -p1 < /tmp/test.patch)")
            log(f"[swebench] applied test_patch (rc={ap.exit_code})", verbosity, "debug")

        log(f"[swebench] {instance_id} provider={provider_name} agent starting",
            verbosity, "normal")
        prompt = build_task_prompt({"system_prompt": SYSTEM_PROMPT, "instruction": problem})
        pr = provider_impl.run_task(
            prompt=prompt, workdir="/testbed", provider_model=provider_model,
            session_name=name, executor=executor,
        )

        diff = _run(executor, "cd /testbed && git diff").stdout
        write_text(logs_dir / "agent.diff", diff)
        # Full raw agent trace (every step/tool-call) + final message + stderr, for analysis.
        write_text(logs_dir / "agent.raw.jsonl", pr.raw_output or "")
        write_text(logs_dir / "agent.stdout.log", pr.stdout or "")
        write_text(logs_dir / "agent.stderr.log", pr.stderr or "")
        provider_evidence = provider_impl.build_provider_evidence(pr)
        evidence_log = ""
        if provider_evidence:
            evidence_log += (
                "<provider_evidence>\n" + provider_evidence.strip() + "\n</provider_evidence>\n"
            )
        evidence_log += "<evidence_diff>\n" + diff[:8000] + "\n</evidence_diff>"

        # Verify: run the instance's own test command(s).
        log(f"[swebench] {instance_id} running tests", verbosity, "normal")
        test_out = ""
        for cmd in test_cmds:
            r = _run(executor, f"cd /testbed && source /opt/miniconda3/bin/activate testbed "
                               f"2>/dev/null; {cmd}")
            test_out += f"$ {cmd}\n{r.stdout}\n{r.stderr}\n"
        write_text(logs_dir / "tests.log", test_out)
        parsed = parse_test_results(test_out, fail_to_pass, pass_to_pass)
        validation_failed = not parsed["resolved"]

        # Feed the judge the AUTHORITATIVE objective gate (not the full pytest log:
        # `pytest -rA` runs the whole repo suite, whose out-of-scope failures would
        # mislead the judge). The judge assesses fix quality given the gate verdict.
        gate = (
            "OBJECTIVE TEST GATE (authoritative — source of truth for correctness):\n"
            f"resolved={parsed['resolved']}\n"
            f"FAIL_TO_PASS (had to start passing): {parsed['fail_to_pass']}\n"
            f"PASS_TO_PASS (had to stay passing): {parsed['pass_to_pass']}\n"
            "Only these tests determine correctness; any other tests in the repo are "
            "out of scope and must be ignored. Judge the quality of the diff below."
        )
        judge_payload = {
            "task": prompt,
            "prep_log": f"base_commit={base_commit}",
            "quality_log": "",
            "validation_log": gate,
            "evidence_log": evidence_log,
        }
        judge_meta = dict(judge_cfg)
        judge_meta["io_dir"] = str(logs_dir.resolve())
        judge_meta["repo_root"] = str(repo_root)
        judge_out = run_judge(judge_payload, judge_meta, str(repo_root))
        write_text(logs_dir / "judge.raw.log", str(judge_out.get("_judge_raw", "")))
    finally:
        executor.close()

    pricing = models_cfg.get("models", {}).get(benchmark_model, {}).get("pricing")
    eval_cost = compute_cost(pr.input_tokens, pr.cached_input_tokens, pr.output_tokens, pricing) \
        if pricing else None

    return {
        "case_id": instance_id,
        "source": "swebench-live",
        "setup": f"{provider_name}__{safe_id(benchmark_model)}",
        "provider": provider_name,
        "model": benchmark_model,
        "provider_model": provider_model,
        "runner": "swebench",
        "executor": "docker",
        "result": {
            "stdout": pr.stdout,
            "stderr": pr.stderr,
            "exit_code": pr.exit_code,
            "elapsed_ms": pr.elapsed_ms,
        },
        "tokens": {
            "input": pr.input_tokens, "cached_input": pr.cached_input_tokens,
            "output": pr.output_tokens, "reasoning": pr.reasoning_tokens, "total": pr.total_tokens,
        },
        "cost_usd": eval_cost,
        "swebench": parsed,
        "scripts": {
            "setup": {"exit_code": 0},
            "quality": {"exit_code": 0},
            "validate": {"exit_code": 0 if not validation_failed else 1},
        },
        "judge": judge_out,
        "scoring": {},
    }


def main() -> None:
    p = argparse.ArgumentParser(prog="python3 -m cli.swebench")
    p.add_argument("--instance", default=None, help="Instance id (default: smallest in split)")
    p.add_argument("--split", default="lite", choices=["lite", "verified", "test", "full"])
    p.add_argument("--config", default="configs/run-matrix.swebench.yaml")
    p.add_argument("--out", default="results-swebench")
    p.add_argument("--scoring", default="configs/scoring.yaml")
    p.add_argument("--efficiency", default="configs/efficiency.yaml")
    p.add_argument("--verbosity", choices=["quiet", "normal", "debug"], default="normal")
    args = p.parse_args()

    repo_root = Path.cwd().resolve()
    models_cfg = load_yaml(repo_root / "configs" / "models.yaml")
    judge_cfg = default_judge_cfg(repo_root)
    efficiency_cfg = load_yaml(Path(args.efficiency)) if Path(args.efficiency).exists() else {}
    run_targets = parse_run_matrix_config(Path(args.config), models_cfg)

    log(f"[swebench] selecting instance split={args.split} "
        f"instance={args.instance or 'smallest'}", args.verbosity, "normal")
    instance = select_instance(args.split, args.instance)
    log(f"[swebench] instance={instance['instance_id']} repo={instance['repo']} "
        f"FAIL_TO_PASS={len(_as_list(instance.get('FAIL_TO_PASS')))} "
        f"PASS_TO_PASS={len(_as_list(instance.get('PASS_TO_PASS')))}", args.verbosity, "normal")

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    run_root = Path(args.out) / timestamp
    run_root.mkdir(parents=True, exist_ok=True)

    results = []
    for target in run_targets:
        rec = run_instance(
            instance, target, repo_root, models_cfg, judge_cfg, run_root, args.verbosity
        )
        # SWE-bench is execution-verified: the objective `resolved` gate IS the metric,
        # so it drives final_score. judge (fix quality) and efficiency are recorded as
        # secondary lenses for the comparison, not the headline.
        resolved = bool(rec["swebench"]["resolved"])
        judge_score = float(rec["judge"].get("score", 0))
        eff = compute_efficiency_score(
            rec["result"]["elapsed_ms"], rec["tokens"]["total"], rec.get("cost_usd"), efficiency_cfg
        )
        rec["scoring"] = {
            "resolved": resolved,
            "judge_score": judge_score,
            "efficiency_score": eff,
            "final_score": 100.0 if resolved else 0.0,
            "validation_failed": not resolved,
        }
        results.append(rec)
        log(f"[swebench] {rec['case_id']} {rec['provider']} resolved={resolved} "
            f"final={rec['scoring']['final_score']} judge={judge_score}",
            args.verbosity, "normal")

    out_path = run_root / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"results": results}, f, indent=2)
    print(f"OK {len(results)} run(s). Results: {out_path}")


if __name__ == "__main__":
    main()

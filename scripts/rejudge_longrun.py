#!/usr/bin/env python3
"""Rejudge completed long-run turns from their exact stored judge prompts.

Usage:
  .venv/bin/python scripts/rejudge_longrun.py <results.json> [<results.json> ...]

The agent execution, validation, tokens, cost, and elapsed time remain untouched.
Only incomplete/failed judge panels are retried, then turn and sequence scores are
recomputed. Each input is backed up beside itself before replacement.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli.main import default_judge_cfg, load_yaml, safe_id  # noqa: E402
from judges.llm_judge import (  # noqa: E402
    JUDGE_PANEL_ATTEMPTS,
    JUDGE_RETRY_BACKOFF_S,
    _cfg_for_model,
    _is_valid_verdict,
    _run_single_judge,
)
from scoring.aggregate import compute_efficiency_score, compute_final_score  # noqa: E402


def _judge_exact_prompt(prompt: str, judge_cfg: Dict, workdir: str) -> Dict:
    models = judge_cfg.get("models") or [judge_cfg.get("model")]

    def one(model: str) -> Dict:
        verdict = _run_single_judge(prompt, _cfg_for_model(judge_cfg, model), workdir)
        verdict["_judge_model"] = model
        return verdict

    by_model: Dict[str, Dict] = {}
    pending = list(models)
    for attempt in range(JUDGE_PANEL_ATTEMPTS):
        if attempt:
            time.sleep(JUDGE_RETRY_BACKOFF_S * attempt)
        with ThreadPoolExecutor(max_workers=len(pending)) as pool:
            for verdict in pool.map(one, pending):
                by_model[verdict["_judge_model"]] = verdict
        pending = [model for model in models if not _is_valid_verdict(by_model[model])]
        if not pending:
            break

    verdicts = [by_model[model] for model in models]
    valid = [verdict for verdict in verdicts if _is_valid_verdict(verdict)]
    if pending:
        data: Dict = {
            "score": 0,
            "reasoning": (
                f"Incomplete panel: {len(valid)}/{len(models)} judges produced a "
                f"verdict after {JUDGE_PANEL_ATTEMPTS} attempts"
            ),
            "issues": [f"{model}: no verdict" for model in pending],
            "confidence": 0.0,
            "_judge_parse_error": True,
            "_judge_incomplete": True,
        }
    else:
        data = {
            "score": round(sum(float(verdict["score"]) for verdict in valid) / len(valid), 2),
            "confidence": round(
                sum(float(verdict.get("confidence") or 0) for verdict in valid) / len(valid),
                3,
            ),
            "reasoning": " | ".join(
                f"{verdict['_judge_model']}={verdict['score']}: "
                + str(verdict.get("reasoning", "")).split("\n")[0][:200]
                for verdict in valid
            ),
            "issues": [issue for verdict in valid for issue in (verdict.get("issues") or [])],
        }

    data["judges"] = [
        {
            "model": verdict["_judge_model"],
            "score": verdict.get("score"),
            "confidence": verdict.get("confidence"),
            "reasoning": verdict.get("reasoning"),
            "issues": verdict.get("issues"),
            "parse_error": bool(verdict.get("_judge_parse_error")),
            "elapsed_ms": verdict.get("_judge_elapsed_ms"),
        }
        for verdict in verdicts
    ]
    data["_judge_raw"] = "\n\n===== JUDGE SEPARATOR =====\n\n".join(
        f"[{verdict['_judge_model']}]\n{verdict.get('_judge_raw', '')}"
        for verdict in verdicts
    )
    data["_judge_exit_code"] = max(
        verdict.get("_judge_exit_code") or 0 for verdict in verdicts
    )
    data["_judge_elapsed_ms"] = sum(
        verdict.get("_judge_elapsed_ms") or 0 for verdict in verdicts
    )
    return data


def _needs_rejudge(turn: Dict) -> bool:
    judge = turn.get("judge") or {}
    return bool(
        judge.get("_judge_incomplete")
        or judge.get("_judge_parse_error")
        or judge.get("score") is None
        or judge.get("confidence") in (0, 0.0)
    )


def _logs_dir(results_path: Path, sequence: Dict, turn_number: int) -> Path:
    run_name = f"{sequence['provider']}__{safe_id(sequence['benchmark_model'])}"
    return (
        results_path.parent
        / sequence["sequence_id"]
        / run_name
        / "turns"
        / f"turn_{turn_number}"
        / "logs"
    )


def rejudge_file(
    results_path: Path, judge_cfg: Dict, scoring_cfg: Dict, efficiency_cfg: Dict
) -> int:
    data = json.loads(results_path.read_text())
    changed = 0

    for sequence in data.get("results", []):
        for turn in sequence.get("turns") or []:
            if not _needs_rejudge(turn):
                continue
            logs_dir = _logs_dir(results_path, sequence, int(turn["turn"]))
            prompts = sorted(logs_dir.glob("_prompt_*.txt"))
            if not prompts:
                raise RuntimeError(f"no stored judge prompt under {logs_dir}")

            meta = dict(judge_cfg)
            meta["io_dir"] = str(logs_dir.resolve())
            meta["repo_root"] = str(Path.cwd().resolve())
            old_score = (turn.get("judge") or {}).get("score")
            print(
                f"[rejudge-longrun] {sequence['sequence_id']} turn={turn['turn']} old={old_score}"
            )
            judge_out = _judge_exact_prompt(prompts[0].read_text(), meta, str(Path.cwd()))
            if judge_out.get("_judge_incomplete"):
                raise RuntimeError(
                    f"panel still incomplete for {sequence['sequence_id']} turn {turn['turn']}"
                )
            print(f"[rejudge-longrun]   new={judge_out.get('score')}")
            turn["judge"] = judge_out

            efficiency = compute_efficiency_score(
                turn["provider"]["elapsed_ms"],
                turn["tokens"]["total"],
                turn.get("cost_usd"),
                efficiency_cfg,
            )
            validation_failed = not bool(turn["validation"]["passed"])
            raw_final = compute_final_score(
                float(judge_out.get("score", 0)), efficiency, scoring_cfg
            )
            penalty = (
                float(scoring_cfg.get("validation_fail_penalty", 25.0))
                if validation_failed
                else 0.0
            )
            turn["scoring"].update(
                {
                    "efficiency_score": efficiency,
                    "raw_final_score": raw_final,
                    "final_score": round(max(0.0, raw_final - penalty), 2),
                    "validation_failed": validation_failed,
                }
            )
            changed += 1

        turns = sequence.get("turns") or []
        if turns:
            passed = sum(bool(turn["validation"]["passed"]) for turn in turns)
            score_sum = sum(float(turn["scoring"]["final_score"]) for turn in turns)
            sequence["aggregate"].update(
                {
                    "total_turns": len(turns),
                    "passed": passed,
                    "pass_rate": round(passed / len(turns), 4),
                    "sum_final_score": round(score_sum, 2),
                    "avg_final_score": round(score_sum / len(turns), 2),
                }
            )

    if changed:
        backup = Path(str(results_path) + ".pre-rejudge.bak")
        if not backup.exists():
            shutil.copy2(results_path, backup)
        results_path.write_text(json.dumps(data, indent=2))
    print(f"[rejudge-longrun] updated={changed} file={results_path}")
    return changed


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    root = Path.cwd().resolve()
    judge_cfg = default_judge_cfg(root)
    scoring_cfg = load_yaml(root / "configs" / "scoring.yaml")
    efficiency_cfg = load_yaml(root / "configs" / "efficiency.yaml")
    total = 0
    for raw in sys.argv[1:]:
        total += rejudge_file(Path(raw), judge_cfg, scoring_cfg, efficiency_cfg)
    print(f"[rejudge-longrun] total_updated={total}")


if __name__ == "__main__":
    main()

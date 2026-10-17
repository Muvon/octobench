from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from cli import longrun
from providers.base import ProviderRunResult
from runners.executor import HostExecutor
from scripts import gold_scorecard
from scoring.aggregate import compute_efficiency_score, compute_final_score


class _Executor(HostExecutor):
    def __init__(self, workspace: Path, case_dir: Path) -> None:
        super().__init__(workspace, case_dir, case_dir / "octomind.toml")
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _Provider:
    def __init__(self) -> None:
        self.calls = 0

    def run_task(self, **kwargs) -> ProviderRunResult:
        self.calls += 1
        timer = threading.Timer(0.1, lambda: os.kill(os.getpid(), signal.SIGTERM))
        timer.start()
        started_at = time.monotonic()
        try:
            proc = kwargs["executor"].run(
                [
                    sys.executable,
                    "-u",
                    "-c",
                    "import time; print('started', flush=True); time.sleep(60)",
                ]
            )
        finally:
            timer.cancel()
        self.elapsed_before_return_ms = int((time.monotonic() - started_at) * 1000)
        return ProviderRunResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.exit_code,
            elapsed_ms=750,
            input_tokens=1_000_000,
            cached_input_tokens=500_000,
            output_tokens=100_000,
            reasoning_tokens=50_000,
            total_tokens=1_650_000,
            aux_input_tokens=100_000,
            aux_output_tokens=50_000,
            aux_cost_usd=0.36,
            session_id="session-1",
            raw_output=proc.stdout,
        )

    def build_provider_evidence(self, _result: ProviderRunResult) -> str:
        return ""


class LongrunSequenceCapTest(unittest.TestCase):
    def test_sigterm_during_provider_keeps_usage_and_writes_all_turns(self) -> None:
        sequence = {
            "id": "longrun_cpp_example",
            "system_prompt": "system",
            "meta": {"repo": "https://example.test/repo"},
            "turns": [
                {
                    "name": f"turn {number}",
                    "instruction": f"instruction {number}",
                    "gold_sha": str(number) * 40,
                    "test_paths": [f"test_{number}.py"],
                    "test_command": "true",
                }
                for number in range(1, 5)
            ],
        }
        args = argparse.Namespace(max_turns=4)
        provider = _Provider()

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            workspace = tmp / "workspace"
            workspace.mkdir()
            run_dir = tmp / "run"
            executor = _Executor(workspace, tmp)
            cleanup_calls = []

            with (
                patch.object(longrun, "get_provider", return_value=provider),
                patch.object(longrun, "ensure_workspace", return_value=workspace),
                patch.object(longrun, "make_executor", return_value=executor),
                patch.object(
                    longrun,
                    "run_case_script",
                    return_value={"exit_code": 0, "stdout": "setup", "stderr": ""},
                ),
                patch.object(longrun, "install_guardrails"),
                patch.object(longrun, "snapshot_files", return_value={}),
                patch.object(longrun, "diff_snapshots", return_value={}),
                patch.object(
                    longrun,
                    "_validate_turn",
                    return_value={"exit_code": 0, "stdout": "pass", "stderr": ""},
                ) as validate_turn,
                patch.object(longrun, "run_judge", return_value={"score": 80}) as run_judge,
                patch.object(
                    longrun,
                    "clean_workspace",
                    side_effect=lambda *call_args: cleanup_calls.append(call_args),
                ),
            ):
                record = longrun._run_sequence(
                    sequence=sequence,
                    sequence_dir=tmp,
                    provider_name="opencode",
                    benchmark_model="glm-5.3-alibaba",
                    provider_model="alibaba/glm-5.3",
                    run_dir=run_dir,
                    args=args,
                    judge_cfg={},
                    scoring_cfg={"judge_weight": 0.85, "efficiency_weight": 0.15},
                    efficiency_cfg={
                        "latency_ms": 8000,
                        "cost_usd": 0.2,
                        "weight_latency": 0.4,
                        "weight_cost": 0.4,
                    },
                    pricing={"input": 1.4, "cached_input": 0.26, "output": 4.4},
                    reasoning_effort=None,
                    verbosity="quiet",
                )

            validate_turn.assert_not_called()
            run_judge.assert_not_called()
            self.assertTrue(executor.closed)
            self.assertEqual(len(cleanup_calls), 1)
            self.assertLess(provider.elapsed_before_return_ms, 5000)
            self.assertEqual(
                [turn["status"] for turn in record["turns"]],
                ["killed_by_sequence_cap", "not_run", "not_run", "not_run"],
            )
            self.assertEqual(record["error"], "sequence_timeout")
            self.assertEqual(record["aggregate"]["total_turns"], 4)
            self.assertEqual(record["aggregate"]["passed"], 0)
            self.assertEqual(record["aggregate"]["pass_rate"], 0)
            self.assertEqual(record["aggregate"]["total_tokens"], 1_800_000)
            self.assertEqual(record["aggregate"]["total_cost_usd"], 2.55)
            killed = record["turns"][0]
            self.assertEqual(killed["provider"]["elapsed_ms"], 750)
            self.assertEqual(killed["provider"]["exit_code"], 124)
            self.assertEqual(killed["provider"]["stdout"], "started\n")
            self.assertEqual(killed["validation"], {"exit_code": None, "passed": False})
            self.assertEqual(
                killed["tokens"],
                {
                    "semantics": "separate_reasoning_v1",
                    "input": 1_000_000,
                    "cached_input": 500_000,
                    "output": 100_000,
                    "reasoning": 50_000,
                    "aux_input": 100_000,
                    "aux_output": 50_000,
                    "total": 1_800_000,
                },
            )
            self.assertEqual(killed["cost_usd"], 2.55)
            efficiency = compute_efficiency_score(
                750,
                2.55,
                {
                    "latency_ms": 8000,
                    "cost_usd": 0.2,
                    "weight_latency": 0.4,
                    "weight_cost": 0.4,
                },
            )
            raw_final = compute_final_score(
                0.0,
                efficiency,
                {"judge_weight": 0.85, "efficiency_weight": 0.15},
            )
            self.assertEqual(
                killed["scoring"],
                {
                    "efficiency_score": efficiency,
                    "raw_final_score": raw_final,
                    "final_score": 0,
                    "validation_failed": True,
                },
            )
            not_run = record["turns"][1]
            self.assertEqual(not_run["provider"]["elapsed_ms"], 0)
            self.assertIsNone(not_run["provider"]["exit_code"])
            self.assertTrue(
                all(
                    not_run["tokens"][key] == 0
                    for key in (
                        "input",
                        "cached_input",
                        "output",
                        "reasoning",
                        "aux_input",
                        "aux_output",
                        "total",
                    )
                )
            )
            self.assertEqual(not_run["cost_usd"], 0.0)

            sequence_path = tmp / "sequence.yaml"
            sequence_path.write_text("id: longrun_cpp_example\n")
            out_dir = tmp / "results-r1"
            logs = []
            argv = [
                "cli.longrun",
                "run",
                "--sequence",
                str(sequence_path),
                "--providers",
                "opencode",
                "--models",
                "glm-5.3-alibaba",
                "--out",
                str(out_dir),
                "--verbosity",
                "normal",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(longrun.signal, "signal"),
                patch.object(longrun, "enforce_clean_bench"),
                patch.object(longrun, "_run_sequence", return_value=record),
                patch.object(
                    longrun, "probe_provider_health", return_value=(True, "")
                ),
                patch.object(longrun.time, "strftime", return_value="20261007-020051"),
                patch.object(
                    longrun,
                    "log",
                    side_effect=lambda message, *_args: logs.append(message),
                ),
            ):
                with self.assertRaisesRegex(SystemExit, "124"):
                    longrun.main()

            results_path = out_dir / "20261007-020051" / "results.json"
            stored = json.loads(results_path.read_text())
            self.assertEqual(stored, {"results": [record]})
            self.assertIn(
                "[longrun] SEQUENCE-CAP sequence=longrun_cpp_example completed=0/4",
                logs,
            )

            rounds = gold_scorecard.load_column(str(results_path), None)
            stats = gold_scorecard._round_stats(rounds["r1"].values())
            self.assertEqual(stats.longrun_turns_passed, 0)
            self.assertEqual(stats.longrun_turns_total, 4)
            self.assertEqual(stats.totals.unknown_costs, 0)
            report = gold_scorecard.render([("recovered", rounds)])
            self.assertIn("0.0% (95% CI 0.0%–49.0%) · 0/4 pooled", report)
            self.assertNotIn("UNKNOWN cost", report)

    def test_unhealthy_probe_keeps_completed_results_and_writes_sidecar(self) -> None:
        completed = {
            "sequence_id": "completed_sequence",
            "turns": [],
            "aggregate": {
                "total_turns": 1,
                "passed": 1,
                "sum_final_score": 100,
            },
        }
        capped = {
            "sequence_id": "capped_sequence",
            "turns": [
                {"status": "killed_by_sequence_cap"},
                {"status": "not_run"},
            ],
            "aggregate": {
                "total_turns": 2,
                "passed": 0,
                "sum_final_score": 0,
            },
            "error": "sequence_timeout",
        }

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            sequences_dir = tmp / "sequences"
            for sequence_id in ("completed_sequence", "capped_sequence"):
                sequence_dir = sequences_dir / sequence_id
                sequence_dir.mkdir(parents=True)
                (sequence_dir / "sequence.yaml").write_text(
                    f"id: {sequence_id}\n", encoding="utf-8"
                )
            out_dir = tmp / "results-r1"
            logs = []
            argv = [
                "cli.longrun",
                "run",
                "--sequences",
                str(sequences_dir),
                "--providers",
                "opencode",
                "--models",
                "glm-5.3-alibaba",
                "--out",
                str(out_dir),
                "--verbosity",
                "normal",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(longrun.signal, "signal"),
                patch.object(longrun, "enforce_clean_bench"),
                # rglob order is filesystem order; the cap ends the run, so the
                # completed sequence must be discovered first.
                patch.object(
                    longrun,
                    "_find_sequence_files",
                    return_value=[
                        sequences_dir / sequence_id / "sequence.yaml"
                        for sequence_id in ("completed_sequence", "capped_sequence")
                    ],
                ),
                patch.object(longrun, "_run_sequence", side_effect=[completed, capped]),
                patch.object(
                    longrun,
                    "probe_provider_health",
                    return_value=(False, "quota exhausted"),
                ),
                patch.object(longrun.time, "strftime", return_value="20261007-030000"),
                patch.object(
                    longrun,
                    "log",
                    side_effect=lambda message, *_args: logs.append(message),
                ),
            ):
                with self.assertRaisesRegex(SystemExit, "124"):
                    longrun.main()

            run_root = out_dir / "20261007-030000"
            stored = json.loads((run_root / "results.json").read_text())
            self.assertEqual(stored, {"results": [completed]})
            unavailable = json.loads(
                (run_root / "results.provider_unavailable.json").read_text()
            )
            unavailable_record = unavailable["results"][0]
            self.assertEqual(unavailable_record["sequence_id"], "capped_sequence")
            self.assertEqual(unavailable_record["error"], "provider_unavailable")
            self.assertEqual(
                unavailable_record["provider_unavailable"], "quota exhausted"
            )
            self.assertNotIn(capped, stored["results"])
            self.assertIn(
                "[longrun] PROVIDER-UNAVAILABLE sequence=capped_sequence "
                "detail=quota exhausted",
                logs,
            )

    def test_sigterm_after_provider_return_keeps_provider_usage(self) -> None:
        sequence = {
            "id": "longrun_cpp_example",
            "system_prompt": "system",
            "meta": {"repo": "https://example.test/repo"},
            "turns": [
                {
                    "name": "turn 1",
                    "instruction": "instruction 1",
                    "gold_sha": "1" * 40,
                    "test_paths": ["test_1.py"],
                    "test_command": "true",
                },
                {
                    "name": "turn 2",
                    "instruction": "instruction 2",
                    "gold_sha": "2" * 40,
                    "test_paths": ["test_2.py"],
                    "test_command": "true",
                },
            ],
        }

        class CompletedProvider:
            def run_task(self, **_kwargs) -> ProviderRunResult:
                return ProviderRunResult(
                    stdout="done",
                    stderr="",
                    exit_code=0,
                    elapsed_ms=500,
                    input_tokens=10,
                    cached_input_tokens=20,
                    output_tokens=30,
                    reasoning_tokens=40,
                    total_tokens=100,
                    session_id="session-1",
                )

            def build_provider_evidence(self, _result: ProviderRunResult) -> str:
                return ""

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            workspace = tmp / "workspace"
            workspace.mkdir()
            executor = _Executor(workspace, tmp)
            with (
                patch.object(longrun, "get_provider", return_value=CompletedProvider()),
                patch.object(longrun, "ensure_workspace", return_value=workspace),
                patch.object(longrun, "make_executor", return_value=executor),
                patch.object(
                    longrun,
                    "run_case_script",
                    return_value={"exit_code": 0, "stdout": "setup", "stderr": ""},
                ),
                patch.object(longrun, "install_guardrails"),
                patch.object(longrun, "snapshot_files", return_value={}),
                patch.object(longrun, "_validate_turn", side_effect=SystemExit(124)),
                patch.object(longrun, "clean_workspace"),
            ):
                record = longrun._run_sequence(
                    sequence,
                    tmp,
                    "opencode",
                    "glm-5.3-alibaba",
                    "alibaba/glm-5.3",
                    tmp / "run",
                    argparse.Namespace(max_turns=2),
                    {},
                    {"judge_weight": 0.85, "efficiency_weight": 0.15},
                    {
                        "latency_ms": 8000,
                        "cost_usd": 0.2,
                        "weight_latency": 0.4,
                        "weight_cost": 0.4,
                    },
                    {"input": 1.4, "cached_input": 0.26, "output": 4.4},
                    None,
                    "quiet",
                )

            killed = record["turns"][0]
            self.assertEqual(killed["status"], "killed_by_sequence_cap")
            self.assertEqual(killed["tokens"]["total"], 100)
            self.assertAlmostEqual(killed["cost_usd"], 0.0003272)
            self.assertEqual(record["turns"][1]["status"], "not_run")


if __name__ == "__main__":
    unittest.main()

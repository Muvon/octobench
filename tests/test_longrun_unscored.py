from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import List, Optional
from unittest.mock import Mock, patch

from cli import longrun
from providers.base import ProviderRunResult
from scripts import gold_scorecard, longrun_table, summary_longrun


def _turn(number: int) -> dict:
    return {
        "name": f"turn {number}",
        "instruction": f"instruction {number}",
        "gold_sha": str(number) * 40,
        "test_paths": [f"test_{number}.py"],
        "test_command": "true",
    }


class LongrunUnscoredManifestTest(unittest.TestCase):
    def test_requires_reason_and_enforces_both_limits(self) -> None:
        missing_reason = [_turn(number) for number in range(1, 6)]
        missing_reason[0]["unscored"] = True
        self.assertIn(
            "turn 1: unscored_reason is required when unscored",
            longrun._unscored_turn_errors(missing_reason),
        )

        ratio_exceeded = [_turn(number) for number in range(1, 10)]
        for turn in ratio_exceeded[:2]:
            turn.update(unscored=True, unscored_reason="not fairly testable")
        self.assertEqual(
            longrun._unscored_turn_errors(ratio_exceeded),
            ["has 2 unscored turns (maximum floor(9/5)=1)"],
        )

        absolute_limit_exceeded = [_turn(number) for number in range(1, 16)]
        for turn in absolute_limit_exceeded[:3]:
            turn.update(unscored=True, unscored_reason="not fairly testable")
        self.assertEqual(
            longrun._unscored_turn_errors(absolute_limit_exceeded),
            ["has 3 unscored turns (maximum 2)"],
        )

        valid = [_turn(number) for number in range(1, 11)]
        for turn in valid[:2]:
            turn.update(unscored=True, unscored_reason="not fairly testable")
        self.assertEqual(longrun._unscored_turn_errors(valid), [])

    def test_run_refuses_invalid_unscored_manifest_before_provider_setup(self) -> None:
        turns = [_turn(number) for number in range(1, 6)]
        turns[0]["unscored"] = True
        sequence = {
            "id": "invalid_sequence",
            "system_prompt": "system",
            "meta": {"repo": "https://example.test/repo"},
            "turns": turns,
        }
        with patch.object(longrun, "get_provider") as get_provider:
            with self.assertRaisesRegex(
                ValueError,
                "turn 1: unscored_reason is required when unscored",
            ):
                longrun._run_sequence(
                    sequence,
                    Path("sequence"),
                    "codex",
                    "model",
                    "provider-model",
                    Path("run"),
                    argparse.Namespace(max_turns=None),
                    {},
                    {},
                    {},
                    {},
                    None,
                    "quiet",
                )
        get_provider.assert_not_called()


class LongrunUnscoredRunTest(unittest.TestCase):
    def test_skips_agent_validation_and_judge_then_restores_gold(self) -> None:
        turns = [_turn(number) for number in range(1, 6)]
        turns[1].update(
            unscored=True,
            unscored_reason="upstream test binds to an undisclosed implementation detail",
        )
        sequence = {
            "id": "longrun_python_example",
            "system_prompt": "system prompt",
            "meta": {"repo": "https://example.test/repo"},
            "turns": turns,
        }
        provider = Mock()
        provider.run_task.side_effect = [
            ProviderRunResult(
                stdout="done",
                stderr="",
                exit_code=0,
                elapsed_ms=100,
                input_tokens=10,
                cached_input_tokens=20,
                output_tokens=30,
                reasoning_tokens=40,
                total_tokens=100,
                session_id="session-1",
            ),
            ProviderRunResult(
                stdout="done",
                stderr="",
                exit_code=0,
                elapsed_ms=100,
                input_tokens=10,
                cached_input_tokens=20,
                output_tokens=30,
                reasoning_tokens=40,
                total_tokens=100,
                session_id="session-1",
            ),
        ]
        provider.build_provider_evidence.return_value = ""

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            workspace = tmp / "workspace"
            workspace.mkdir()
            executor = Mock()
            executor.workspace_host_path.return_value = workspace
            executor.container_workspace.return_value = "/workspace"
            executor.end_provider_call.return_value = False
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
                patch.object(
                    longrun,
                    "diff_snapshots",
                    return_value={"added": [], "deleted": [], "modified": []},
                ),
                patch.object(longrun, "_restore_dependency", return_value=True) as restore,
                patch.object(
                    longrun,
                    "_validate_turn",
                    return_value={"exit_code": 0, "stdout": "pass", "stderr": ""},
                ) as validate,
                patch.object(longrun, "run_judge", return_value={"score": 80}) as judge,
                patch.object(longrun, "clean_workspace"),
                patch.dict("os.environ", {"OCTOBENCH_FRESH_SESSIONS": "0"}),
            ):
                result = longrun._run_sequence(
                    sequence,
                    tmp,
                    "codex",
                    "model",
                    "provider-model",
                    tmp / "run",
                    argparse.Namespace(max_turns=3),
                    {},
                    {"judge_weight": 0.85, "efficiency_weight": 0.15},
                    {
                        "latency_ms": 8000,
                        "cost_usd": 0.2,
                        "weight_latency": 0.4,
                        "weight_cost": 0.4,
                    },
                    {"input": 1.0, "cached_input": 0.1, "output": 2.0},
                    None,
                    "quiet",
                )

        self.assertEqual(provider.run_task.call_count, 2)
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(judge.call_count, 2)
        restore.assert_called_once_with(
            executor,
            "https://example.test/repo",
            "2" * 40,
            ["test_2.py"],
            2,
            "quiet",
        )
        prompts = [call.kwargs["prompt"] for call in provider.run_task.call_args_list]
        self.assertIn("System:\nsystem prompt", prompts[0])
        self.assertEqual(prompts[1], "instruction 3\n")
        self.assertNotIn("instruction 2", "\n".join(prompts))

        unscored = result["turns"][1]
        self.assertEqual(unscored["status"], "unscored")
        self.assertEqual(
            unscored["unscored_reason"],
            "upstream test binds to an undisclosed implementation detail",
        )
        self.assertIsNone(unscored["provider"]["elapsed_ms"])
        metric_tokens = {
            key: value
            for key, value in unscored["tokens"].items()
            if key != "semantics"
        }
        self.assertTrue(all(value is None for value in metric_tokens.values()))
        self.assertIsNone(unscored["cost_usd"])
        self.assertEqual(result["aggregate"]["total_turns"], 2)
        self.assertEqual(result["aggregate"]["unscored"], 1)
        self.assertEqual(result["aggregate"]["passed"], 2)


class LongrunUnscoredReportingTest(unittest.TestCase):
    def test_scorecard_marks_restored_and_post_unscored_turns_assisted(self) -> None:
        def scored(
            number: int, *, passed: bool = True, restored: Optional[List[int]] = None
        ) -> dict:
            return {
                "turn": number,
                "status": "completed",
                "restored_dependencies": restored or [],
                "session_mode": "resumed",
                "provider": {"elapsed_ms": 1000, "session_id": "session"},
                "tokens": {
                    "input": 1,
                    "cached_input": 0,
                    "output": 1,
                    "reasoning": 0,
                },
                "cost_usd": 0.1,
                "validation": {"passed": passed},
            }

        unscored = longrun._unscored_turn_result(
            3,
            {
                "name": "unscored",
                "instruction": "hidden from agent",
                "unscored_reason": "not fairly testable",
            },
            "resumed",
        )
        record = {
            "sequence_id": "longrun_python_example",
            "provider": "codex",
            "benchmark_model": "model",
            "turns": [
                scored(1),
                scored(2, restored=[1]),
                unscored,
                scored(4),
                scored(5, passed=False),
            ],
        }

        with patch.object(gold_scorecard, "extract_efficiency", return_value=None):
            items = list(
                gold_scorecard._longrun_items(
                    record, None, Path("results-r1/results.json")
                )
            )

        scored_items = [item for item in items if item.kind == "longrun"]
        self.assertEqual(
            [item.assisted for item in scored_items], [False, True, True, True]
        )
        stats = gold_scorecard._round_stats(items)
        self.assertEqual(stats.assisted_turns_passed, 2)
        self.assertEqual(stats.assisted_turns_total, 3)
        report = gold_scorecard.render(
            [("client", {"r1": {item.key: item for item in items}})]
        )
        self.assertIn("solve — assisted long-run turns passed/total | 2/3 pooled", report)

    def test_reporters_exclude_unscored_metrics_and_show_count(self) -> None:
        completed = {
            "turn": 1,
            "name": "scored",
            "status": "completed",
            "provider": {"elapsed_ms": 120_000, "session_id": "session"},
            "tokens": {
                "input": 100,
                "cached_input": 20,
                "output": 30,
                "reasoning": 10,
                "total": 160,
            },
            "cost_usd": 1.25,
            "validation": {"passed": True},
            "judge": {"score": 80},
            "scoring": {"final_score": 75.0},
        }
        unscored = longrun._unscored_turn_result(
            2,
            {
                "name": "unscored",
                "instruction": "hidden from agent",
                "unscored_reason": "not fairly testable",
            },
            "resumed",
        )
        record = {
            "sequence_id": "longrun_python_example",
            "provider": "codex",
            "benchmark_model": "model",
            "turns": [completed, unscored],
            "aggregate": {
                "total_turns": 2,
                "passed": 2,
                "sum_final_score": 150,
                "total_cost_usd": 99,
                "total_tokens": 999,
            },
        }

        table_cell = longrun_table.cell(record)
        self.assertIn("1/1", table_cell)
        self.assertIn("Σ75.0", table_cell)
        self.assertIn("$1.25", table_cell)
        self.assertIn("unscored:1", table_cell)

        with patch.object(gold_scorecard, "extract_efficiency", return_value=None):
            items = list(
                gold_scorecard._longrun_items(record, None, Path("results-r1/results.json"))
            )
        stats = gold_scorecard._round_stats(items)
        self.assertEqual(stats.longrun_turns_passed, 1)
        self.assertEqual(stats.longrun_turns_total, 1)
        self.assertEqual(stats.longrun_turns_unscored, 1)
        self.assertEqual(stats.totals.item_count, 1)
        report = gold_scorecard.render([("client", {"r1": {item.key: item for item in items}})])
        self.assertIn("not scored — long-run turns", report)
        self.assertIn("1.0", report)

        with tempfile.TemporaryDirectory() as raw_tmp:
            results_path = Path(raw_tmp) / "results.json"
            results_path.write_text(json.dumps({"results": [record]}))
            stdout = io.StringIO()
            with patch("sys.argv", ["summary_longrun.py", "--verbose", str(results_path)]):
                with redirect_stdout(stdout):
                    summary_longrun.main()
        self.assertIn("UNSCORED", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import math
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from runners.executor import HostExecutor
from scoring.efficiency import (
    EfficiencyMetrics,
    extract_claude,
    extract_codex,
    extract_efficiency,
    extract_octomind,
    extract_opencode,
    geometric_mean,
    is_filler_call,
    relative_indexes,
)
from scripts import gold_scorecard


def _write_jsonl(path: Path, rows: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _insert_opencode_prompt(
    db: sqlite3.Connection, message_id: str, session_id: str, created: int
) -> None:
    db.execute(
        "INSERT INTO part VALUES (?, ?, ?, ?, ?, ?)",
        (
            f"{message_id}-prompt",
            message_id,
            session_id,
            created,
            created,
            json.dumps({"type": "text", "text": "task"}),
        ),
    )


class EfficiencyExtractorTest(unittest.TestCase):
    def test_timeout_kills_sigterm_ignoring_process_group_and_freezes_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            executor = HostExecutor(root, root, root / "octomind.toml")
            executor.case_timeout_s = 0.05
            child = """
import signal
import time

def handle_sigterm(_signum, _frame):
    print("after-cap", flush=True)

signal.signal(signal.SIGTERM, handle_sigterm)
print("before-cap", flush=True)
time.sleep(10)
"""
            started = time.monotonic()

            result = executor.run([sys.executable, "-c", child])

            self.assertLess(time.monotonic() - started, 3)
            self.assertEqual(result.exit_code, 124)
            self.assertIn("before-cap", result.stdout)
            self.assertNotIn("after-cap", result.stdout)

    def test_octomind_busy_is_union_of_model_tool_and_delivered_job_intervals(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            record_dir = Path(raw_tmp) / "run"
            _write_jsonl(
                record_dir / "logs" / "provider.raw.jsonl",
                [
                    {
                        "type": "tool_use",
                        "tool_id": "1",
                        "tool": "shell",
                        "params": {"command": "echo hi"},
                    },
                    {"type": "tool_result", "tool_id": "1", "content": "hi"},
                    {
                        "type": "tool_use",
                        "tool_id": "2",
                        "tool": "shell",
                        "params": {"command": "echo hi"},
                    },
                    {"type": "tool_result", "tool_id": "2", "content": "hi"},
                    {"type": "tool_use", "tool_id": "3", "tool": "view", "params": {"path": "x"}},
                    {"type": "tool_result", "tool_id": "3", "content": "x"},
                ],
            )
            session_rows = [
                {
                    "type": "SUMMARY",
                    "timestamp": 0,
                    "session_info": {
                        "total_api_time_ms": 0,
                        "total_tool_time_ms": 0,
                        "turn_timing": {"completed": 0},
                    },
                },
                {"role": "system", "content": "start", "timestamp": 0},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{"id": "tool-a", "name": "shell"}],
                    "timestamp": 2,
                },
                {
                    "role": "tool",
                    "name": "shell",
                    "tool_call_id": "tool-a",
                    "content": (
                        "Still running after the foreground limit — moved to "
                        "background job `job-a` (PID 1)."
                    ),
                    "timestamp": 3,
                },
                {"role": "assistant", "content": "working", "timestamp": 5},
                {
                    "role": "user",
                    "content": (
                        '<background_job resource="octofs://jobs/job-a">'
                        "done</background_job>"
                    ),
                    "timestamp": 8,
                },
                {
                    "role": "assistant",
                    "content": "done",
                    "timestamp": 9,
                },
                {
                    "type": "SUMMARY",
                    "timestamp": 12,
                    "session_info": {
                        "total_api_time_ms": 4000,
                        "total_tool_time_ms": 1000,
                        "turn_timing": {"completed": 1},
                    },
                },
            ]
            source = record_dir / "session.jsonl"
            _write_jsonl(source, session_rows)
            destination = (
                record_dir / "state" / "octomind" / "sessions" / "session.jsonl.zst"
            )
            destination.parent.mkdir(parents=True)
            subprocess.run(
                ["zstd", "-q", "-f", str(source), "-o", str(destination)],
                check=True,
            )

            metrics = extract_octomind(record_dir, 12_000)

            self.assertEqual(metrics.model_ms, 4000)
            self.assertEqual(metrics.tool_ms, 1000)
            self.assertEqual(metrics.own_job_ms, 5000)
            self.assertEqual(metrics.stuck_wait_ms, 0)
            self.assertEqual(metrics.busy_ms, 9000)
            self.assertEqual(metrics.idle_ms, 3000)
            self.assertEqual(metrics.longest_silent_gap_ms, 3000)
            self.assertEqual(metrics.tail_ms, 3000)
            self.assertEqual(metrics.tool_calls, 3)
            self.assertEqual(metrics.repeat_calls, 1)
            self.assertEqual(metrics.filler_calls, 2)

    def test_octomind_only_completed_jobs_are_busy(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            record_dir = Path(raw_tmp) / "run"
            session_rows = [
                {
                    "type": "SUMMARY",
                    "timestamp": 0,
                    "session_info": {
                        "total_api_time_ms": 0,
                        "total_tool_time_ms": 0,
                        "turn_timing": {"completed": 0},
                    },
                },
                {
                    "role": "tool",
                    "name": "shell",
                    "content": "moved to background job `done`",
                    "timestamp": 1,
                },
                {
                    "role": "tool",
                    "name": "shell",
                    "content": "moved to background job `never`",
                    "timestamp": 2,
                },
                {
                    "role": "tool",
                    "name": "shell",
                    "content": "moved to background job `checked`",
                    "timestamp": 3,
                },
                {
                    "role": "user",
                    "content": '<background_job resource="octofs://jobs/done">done</background_job>',
                    "timestamp": 5,
                },
                {
                    "role": "user",
                    "content": (
                        '<background_job resource="octofs://jobs/checked" '
                        'state="status_check">still running</background_job>'
                    ),
                    "timestamp": 8,
                },
                {
                    "type": "SUMMARY",
                    "timestamp": 10,
                    "session_info": {
                        "total_api_time_ms": 0,
                        "total_tool_time_ms": 0,
                        "turn_timing": {"completed": 1},
                    },
                },
            ]
            source = record_dir / "session.jsonl"
            _write_jsonl(source, session_rows)
            destination = (
                record_dir / "state" / "octomind" / "sessions" / "session.jsonl.zst"
            )
            destination.parent.mkdir(parents=True)
            subprocess.run(
                ["zstd", "-q", "-f", str(source), "-o", str(destination)],
                check=True,
            )

            metrics = extract_octomind(record_dir, 10_000)

            self.assertEqual(metrics.own_job_ms, 4000)
            self.assertEqual(metrics.stuck_wait_ms, 8000)
            self.assertEqual(metrics.busy_ms, 4000)
            self.assertEqual(metrics.idle_ms, 6000)

    def test_opencode_database_without_exit_has_unknown_tail(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            record_dir = Path(raw_tmp) / "run"
            db_path = record_dir / "state" / "opencode" / "opencode.db"
            db_path.parent.mkdir(parents=True)
            db = sqlite3.connect(db_path)
            db.executescript(
                """
                CREATE TABLE session (
                    id TEXT PRIMARY KEY, parent_id TEXT, time_created INTEGER, time_updated INTEGER
                );
                CREATE TABLE message (
                    id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER,
                    time_updated INTEGER, data TEXT
                );
                CREATE TABLE part (
                    id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT,
                    time_created INTEGER, time_updated INTEGER, data TEXT
                );
                """
            )
            db.execute("INSERT INTO session VALUES ('root', NULL, 1000, 9000)")
            db.executemany(
                "INSERT INTO message VALUES (?, 'root', ?, ?, ?)",
                [
                    ("user", 1000, 1000, json.dumps({"role": "user", "time": {"created": 1000}})),
                    (
                        "assistant",
                        1000,
                        7000,
                        json.dumps(
                            {
                                "role": "assistant",
                                "time": {"created": 1000, "completed": 7000},
                            }
                        ),
                    ),
                ],
            )
            db.executemany(
                "INSERT INTO part VALUES (?, 'assistant', 'root', ?, ?, ?)",
                [
                    (
                        "tool",
                        3000,
                        5000,
                        json.dumps(
                            {
                                "type": "tool",
                                "tool": "bash",
                                "state": {
                                    "input": {"command": "true"},
                                    "output": "",
                                    "time": {"start": 3000, "end": 5000},
                                },
                            }
                        ),
                    ),
                    (
                        "text",
                        6000,
                        7000,
                        json.dumps(
                            {
                                "type": "text",
                                "text": "done",
                                "time": {"start": 6000, "end": 7000},
                            }
                        ),
                    ),
                ],
            )
            _insert_opencode_prompt(db, "user", "root", 1000)
            db.commit()
            db.close()

            metrics = extract_opencode(record_dir, 8000)

            self.assertEqual(metrics.model_ms, 4000)
            self.assertEqual(metrics.tool_ms, 2000)
            self.assertEqual(metrics.own_job_ms, 0)
            self.assertEqual(metrics.busy_ms, 6000)
            self.assertEqual(metrics.idle_ms, 2000)
            self.assertIsNone(metrics.tail_ms)
            self.assertEqual(metrics.tool_calls, 1)
            self.assertEqual(metrics.repeat_calls, 0)
            self.assertEqual(metrics.filler_calls, 1)

    def test_opencode_compaction_messages_do_not_shift_long_run_turns(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_root = Path(raw_tmp) / "sequence"
            record_dir = run_root / "turns" / "turn_2"
            record_dir.mkdir(parents=True)
            db_path = run_root / "state" / "opencode" / "opencode.db"
            db_path.parent.mkdir(parents=True)
            db = sqlite3.connect(db_path)
            db.executescript(
                """
                CREATE TABLE session (
                    id TEXT PRIMARY KEY, parent_id TEXT, time_created INTEGER, time_updated INTEGER
                );
                CREATE TABLE message (
                    id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER,
                    time_updated INTEGER, data TEXT
                );
                CREATE TABLE part (
                    id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT,
                    time_created INTEGER, time_updated INTEGER, data TEXT
                );
                """
            )
            db.execute("INSERT INTO session VALUES ('root', NULL, 0, 60000)")

            def message(message_id: str, created: int, data: dict[str, object]) -> None:
                db.execute(
                    "INSERT INTO message VALUES (?, 'root', ?, ?, ?)",
                    (message_id, created, created, json.dumps(data)),
                )

            def part(part_id: str, message_id: str, created: int, data: dict[str, object]) -> None:
                db.execute(
                    "INSERT INTO part VALUES (?, ?, 'root', ?, ?, ?)",
                    (part_id, message_id, created, created, json.dumps(data)),
                )

            for message_id, created in (("turn1", 0), ("turn2", 10_000), ("turn3", 50_000)):
                message(message_id, created, {"role": "user"})
                _insert_opencode_prompt(db, message_id, "root", created)
            # Compaction mid-turn 2: a compaction marker and a synthetic continuation.
            message("compaction", 12_000, {"role": "user"})
            part("compaction-part", "compaction", 12_000, {"type": "compaction"})
            message("continue", 12_100, {"role": "user"})
            part(
                "continue-part",
                "continue",
                12_100,
                {"type": "text", "text": "Continue", "synthetic": True},
            )
            for message_id, created, completed in (("a1", 10_000, 12_000), ("a2", 12_200, 45_000)):
                message(
                    message_id,
                    created,
                    {"role": "assistant", "time": {"created": created, "completed": completed}},
                )
            part(
                "bash",
                "a2",
                12_200,
                {
                    "type": "tool",
                    "tool": "bash",
                    "state": {
                        "input": {"command": "make unittest"},
                        "output": "ok",
                        "time": {"start": 12_200, "end": 40_000},
                    },
                },
            )
            db.commit()
            db.close()

            metrics = extract_opencode(record_dir, 40_000)

        # Turn 2 runs from its own prompt to turn 3's prompt, across the compaction.
        self.assertEqual(metrics.tool_ms, 27_800)
        self.assertEqual(metrics.model_ms, 7_000)
        self.assertEqual(metrics.busy_ms, 34_800)
        self.assertEqual(metrics.idle_ms, 5_200)
        self.assertEqual(metrics.tool_calls, 1)

    def test_claude_tail_requires_real_exit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            record_dir = Path(raw_tmp) / "run"
            _write_jsonl(
                record_dir / "logs" / "provider.raw.jsonl",
                [
                    {
                        "type": "assistant",
                        "timestamp": "2026-01-01T00:00:01Z",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "call-1",
                                    "name": "Bash",
                                    "input": {"command": "sleep 1"},
                                }
                            ]
                        },
                    },
                    {
                        "type": "user",
                        "timestamp": "2026-01-01T00:00:03Z",
                        "message": {
                            "content": [
                                {"type": "tool_result", "tool_use_id": "call-1", "content": "done"}
                            ]
                        },
                    },
                    {
                        "type": "assistant",
                        "timestamp": "2026-01-01T00:00:07Z",
                        "message": {"content": [{"type": "text", "text": "final"}]},
                    },
                    {
                        "type": "result",
                        "duration_api_ms": 3000,
                        "duration_ms": 8000,
                        "ttft_stream_ms": 1000,
                    },
                ],
            )

            metrics = extract_claude(record_dir, 10_000)

            self.assertEqual(metrics.model_ms, 3000)
            self.assertEqual(metrics.tool_ms, 2000)
            self.assertEqual(metrics.own_job_ms, 0)
            self.assertEqual(metrics.busy_ms, 6000)
            self.assertEqual(metrics.idle_ms, 4000)
            self.assertEqual(metrics.longest_silent_gap_ms, 4000)
            self.assertIsNone(metrics.tail_ms)
            self.assertEqual(metrics.tool_calls, 1)
            self.assertEqual(metrics.filler_calls, 1)

    def test_claude_incomplete_tool_runs_until_process_exit(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            record_dir = Path(raw_tmp) / "run"
            _write_jsonl(
                record_dir / "logs" / "provider.raw.jsonl",
                [
                    {
                        "type": "assistant",
                        "timestamp": "2026-01-01T00:00:01Z",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "call-1",
                                    "name": "Bash",
                                    "input": {"command": "sleep 30"},
                                }
                            ]
                        },
                    },
                    {
                        "type": "octobench_process_timing",
                        "started_at_ms": 1767225600000,
                        "ended_at_ms": 1767225610000,
                    },
                ],
            )

            metrics = extract_claude(record_dir, 10_000, incomplete=True)

            self.assertIsNone(metrics.model_ms)
            self.assertEqual(metrics.tool_ms, 9000)
            self.assertEqual(metrics.busy_ms, 10_000)
            self.assertEqual(metrics.idle_ms, 0)
            self.assertEqual(metrics.longest_silent_gap_ms, 0)
            self.assertEqual(metrics.tool_calls, 1)
            # The cut-off call never returned, so it is no proven repeat.
            self.assertEqual(metrics.repeat_calls, 0)

    def test_current_codex_retained_rollout_has_known_efficiency(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            record_dir = Path(raw_tmp) / "run"
            _write_jsonl(
                record_dir / "logs" / "codex.rollout.jsonl",
                [
                    {"timestamp": "2026-01-01T00:00:00Z", "type": "turn_context", "payload": {}},
                    {
                        "timestamp": "2026-01-01T00:00:02Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "call_id": "call-1",
                            "name": "exec_command",
                            "arguments": json.dumps({"cmd": ":"}),
                        },
                    },
                    {
                        "timestamp": "2026-01-01T00:00:05Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-1",
                            "output": "ok",
                        },
                    },
                    {
                        "timestamp": "2026-01-01T00:00:08Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "phase": "final_answer",
                        },
                    },
                    {
                        "timestamp": "2026-01-01T00:00:09Z",
                        "type": "event_msg",
                        "payload": {"type": "token_count"},
                    },
                ],
            )
            _write_jsonl(
                record_dir / "logs" / "provider.raw.jsonl",
                [
                    {
                        "type": "octobench_process_timing",
                        "started_at_ms": 1767225600000,
                        "ended_at_ms": 1767225609000,
                    }
                ],
            )

            metrics = extract_codex(record_dir, 10_000)

            self.assertEqual(metrics.model_ms, 5000)
            self.assertEqual(metrics.tool_ms, 3000)
            self.assertEqual(metrics.own_job_ms, 0)
            self.assertEqual(metrics.busy_ms, 8000)
            self.assertEqual(metrics.idle_ms, 2000)
            self.assertEqual(metrics.longest_silent_gap_ms, 1000)
            self.assertEqual(metrics.tail_ms, 1000)
            self.assertEqual(metrics.tool_calls, 1)
            self.assertEqual(metrics.repeat_calls, 0)
            self.assertEqual(metrics.filler_calls, 1)

    def test_codex_killed_mid_tool_keeps_busy_and_proven_repeats(self) -> None:
        def call(ts: str, call_id: str, cmd: str) -> dict[str, object]:
            return {
                "timestamp": ts,
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "call_id": call_id,
                    "name": "exec_command",
                    "arguments": json.dumps({"cmd": cmd}),
                },
            }

        def output(ts: str, call_id: str) -> dict[str, object]:
            return {
                "timestamp": ts,
                "type": "response_item",
                "payload": {"type": "function_call_output", "call_id": call_id, "output": "ok"},
            }

        rollout = [
            {"timestamp": "2026-01-01T00:00:00Z", "type": "turn_context", "payload": {}},
            call("2026-01-01T00:00:02Z", "call-1", ":"),
            output("2026-01-01T00:00:05Z", "call-1"),
            call("2026-01-01T00:00:06Z", "call-2", ":"),
            output("2026-01-01T00:00:07Z", "call-2"),
            call("2026-01-01T00:00:08Z", "call-3", "make test"),
        ]
        timing = {
            "type": "octobench_process_timing",
            "started_at_ms": 1767225600000,
            "ended_at_ms": 1767225620000,
        }
        with tempfile.TemporaryDirectory() as raw_tmp:
            record_dir = Path(raw_tmp) / "run"
            _write_jsonl(record_dir / "logs" / "codex.rollout.jsonl", rollout)
            _write_jsonl(record_dir / "logs" / "provider.raw.jsonl", [timing])

            killed = extract_codex(record_dir, 20_000, incomplete=True)
            finished = extract_codex(record_dir, 20_000)

        # The unfinished call runs until the cap ends the process at 20 s.
        self.assertEqual(killed.tool_ms, 16_000)
        self.assertEqual(killed.model_ms, 4_000)
        self.assertEqual(killed.busy_ms, 20_000)
        self.assertEqual(killed.idle_ms, 0)
        self.assertEqual(killed.tool_calls, 3)
        self.assertEqual(killed.repeat_calls, 1)
        self.assertEqual(killed.filler_calls, 2)
        # The same rollout from a run that finished normally is inconsistent.
        self.assertIsNone(finished.busy_ms)
        self.assertIsNone(finished.repeat_calls)

    def test_not_run_has_no_efficiency_but_capped_turn_keeps_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            results_dir = Path(raw_tmp) / "results-r1"
            results_path = results_dir / "results.json"
            turn_dir = (
                results_dir
                / "longrun_python_demo"
                / "octomind__model"
                / "turns"
                / "turn_1"
            )
            _write_jsonl(
                turn_dir / "logs" / "provider.raw.jsonl",
                [
                    {
                        "type": "tool_use",
                        "tool_id": "command-1",
                        "tool": "shell",
                        "params": {"command": "true"},
                    },
                    {
                        "type": "tool_result",
                        "tool_id": "command-1",
                        "content": "",
                    },
                ],
            )
            session_source = results_dir / "session.jsonl"
            _write_jsonl(
                session_source,
                [
                    {
                        "type": "SUMMARY",
                        "timestamp": 1,
                        "session_info": {
                            "total_api_time_ms": 0,
                            "total_tool_time_ms": 0,
                            "turn_timing": {"completed": 0},
                        },
                    }
                ],
            )
            session_path = (
                results_dir
                / "longrun_python_demo"
                / "octomind__model"
                / "state"
                / "octomind"
                / "sessions"
                / "session.jsonl.zst"
            )
            session_path.parent.mkdir(parents=True)
            subprocess.run(
                ["zstd", "-q", "-f", str(session_source), "-o", str(session_path)],
                check=True,
            )
            record = {
                "sequence_id": "longrun_python_demo",
                "provider": "octomind",
                "benchmark_model": "model",
                "turns": [
                    {
                        "turn": 1,
                        "status": "killed_by_sequence_cap",
                        "tokens": {},
                        "cost_usd": None,
                        "provider": {"elapsed_ms": 1000, "session_id": "session"},
                        "validation": {"passed": False},
                    },
                    {
                        "turn": 2,
                        "status": "not_run",
                        "tokens": {},
                        "cost_usd": 0.0,
                        "provider": {"elapsed_ms": 0, "session_id": "session"},
                        "validation": {"passed": True},
                    },
                ],
            }

            items = list(gold_scorecard._longrun_items(record, None, results_path))

            self.assertEqual(items[0].efficiency.tool_calls, 1)
            self.assertIsNone(items[1].efficiency)
            stats = gold_scorecard._round_stats(items)
            self.assertEqual(stats.longrun_turns_passed, 0)
            self.assertEqual(stats.longrun_turns_total, 2)
            self.assertEqual(stats.totals.item_count, 2)

    def test_octomind_killed_run_uses_truncated_session_intervals(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            record_dir = Path(raw_tmp) / "run"
            session_rows = [
                {
                    "type": "SUMMARY",
                    "timestamp": 0,
                    "session_info": {
                        "total_api_time_ms": 0,
                        "total_tool_time_ms": 0,
                        "turn_timing": {"completed": 0},
                    },
                },
                {
                    "type": "SUMMARY",
                    "timestamp": 0,
                    "session_info": {
                        "total_api_time_ms": 0,
                        "total_tool_time_ms": 0,
                        "turn_timing": {"completed": 0},
                    },
                },
                {"role": "system", "content": "start", "timestamp": 0},
                {"role": "user", "content": "task", "timestamp": 0},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{"id": "shell-1", "name": "shell"}],
                    "timestamp": 100,
                },
                {
                    "role": "tool",
                    "name": "shell",
                    "tool_call_id": "shell-1",
                    "content": "moved to background job `stuck`",
                    "timestamp": 110,
                },
                {"role": "assistant", "content": "waiting", "timestamp": 120},
                {
                    "role": "user",
                    "content": (
                        '<background_job resource="octofs://jobs/stuck" '
                        'state="status_check">still running</background_job>'
                    ),
                    "timestamp": 700,
                },
                {"type": "COMPRESSION_POINT", "timestamp": 700},
                {"role": "system", "content": "start", "timestamp": 0},
                {"role": "assistant", "content": "waiting", "timestamp": 120},
                {"role": "assistant", "content": "still waiting", "timestamp": 710},
            ]
            source = record_dir / "session.jsonl"
            _write_jsonl(source, session_rows)
            destination = (
                record_dir / "state" / "octomind" / "sessions" / "session.jsonl.zst"
            )
            destination.parent.mkdir(parents=True)
            subprocess.run(
                ["zstd", "-q", "-f", str(source), "-o", str(destination)],
                check=True,
            )

            metrics = extract_efficiency(
                "octomind",
                record_dir,
                2_000_000,
                status="killed_by_case_cap",
            )

            self.assertIsNone(metrics.model_ms)
            self.assertEqual(metrics.tool_ms, 10_000)
            self.assertEqual(metrics.busy_ms, 130_000)
            self.assertEqual(metrics.stuck_wait_ms, 1_890_000)
            self.assertEqual(metrics.idle_ms, 1_870_000)
            self.assertEqual(metrics.longest_silent_gap_ms, 1_290_000)
            self.assertIsNone(metrics.tail_ms)

    def test_opencode_child_model_and_real_tool_intervals_are_unioned(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            record_dir = Path(raw_tmp) / "run"
            db_path = record_dir / "state" / "opencode" / "opencode.db"
            db_path.parent.mkdir(parents=True)
            db = sqlite3.connect(db_path)
            db.executescript(
                """
                CREATE TABLE session (
                    id TEXT PRIMARY KEY, parent_id TEXT, time_created INTEGER, time_updated INTEGER
                );
                CREATE TABLE message (
                    id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER,
                    time_updated INTEGER, data TEXT
                );
                CREATE TABLE part (
                    id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT,
                    time_created INTEGER, time_updated INTEGER, data TEXT
                );
                """
            )
            db.executemany(
                "INSERT INTO session VALUES (?, ?, ?, ?)",
                [("root", None, 1000, 9000), ("child", "root", 2000, 8000)],
            )
            db.executemany(
                "INSERT INTO message VALUES (?, ?, ?, ?, ?)",
                [
                    ("user", "root", 1000, 1000, json.dumps({"role": "user"})),
                    (
                        "root-assistant",
                        "root",
                        1000,
                        9000,
                        json.dumps(
                            {"role": "assistant", "time": {"created": 1000, "completed": 9000}}
                        ),
                    ),
                    (
                        "child-assistant",
                        "child",
                        3000,
                        7000,
                        json.dumps(
                            {"role": "assistant", "time": {"created": 3000, "completed": 7000}}
                        ),
                    ),
                ],
            )
            db.executemany(
                "INSERT INTO part VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        "task",
                        "root-assistant",
                        "root",
                        2000,
                        8000,
                        json.dumps(
                            {
                                "type": "tool",
                                "tool": "task",
                                "state": {
                                    "input": {},
                                    "output": "done",
                                    "time": {"start": 2000, "end": 8000},
                                },
                            }
                        ),
                    ),
                    (
                        "bash",
                        "child-assistant",
                        "child",
                        5000,
                        6000,
                        json.dumps(
                            {
                                "type": "tool",
                                "tool": "bash",
                                "state": {
                                    "input": {"command": "true"},
                                    "output": "",
                                    "time": {"start": 5000, "end": 6000},
                                },
                            }
                        ),
                    ),
                ],
            )
            _insert_opencode_prompt(db, "user", "root", 1000)
            db.commit()
            db.close()

            metrics = extract_opencode(record_dir, 8000)

            self.assertEqual(metrics.model_ms, 5000)
            self.assertEqual(metrics.tool_ms, 1000)
            self.assertEqual(metrics.busy_ms, 6000)

    def test_opencode_intervals_are_clamped_to_process_exit(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            record_dir = Path(raw_tmp) / "run"
            db_path = record_dir / "state" / "opencode" / "opencode.db"
            db_path.parent.mkdir(parents=True)
            db = sqlite3.connect(db_path)
            db.executescript(
                """
                CREATE TABLE session (
                    id TEXT PRIMARY KEY, parent_id TEXT, time_created INTEGER, time_updated INTEGER
                );
                CREATE TABLE message (
                    id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER,
                    time_updated INTEGER, data TEXT
                );
                CREATE TABLE part (
                    id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT,
                    time_created INTEGER, time_updated INTEGER, data TEXT
                );
                """
            )
            db.execute("INSERT INTO session VALUES ('root', NULL, 1000, 12000)")
            db.executemany(
                "INSERT INTO message VALUES (?, 'root', ?, ?, ?)",
                [
                    ("user", 1000, 1000, json.dumps({"role": "user"})),
                    (
                        "assistant",
                        1000,
                        12000,
                        json.dumps(
                            {"role": "assistant", "time": {"created": 1000, "completed": 12000}}
                        ),
                    ),
                ],
            )
            db.execute(
                "INSERT INTO part VALUES (?, 'assistant', 'root', ?, ?, ?)",
                (
                    "tool",
                    8000,
                    11000,
                    json.dumps(
                        {
                            "type": "tool",
                            "tool": "bash",
                            "state": {
                                "input": {"command": "true"},
                                "output": "",
                                "time": {"start": 8000, "end": 11000},
                            },
                        }
                    ),
                ),
            )
            _insert_opencode_prompt(db, "user", "root", 1000)
            db.commit()
            db.close()
            _write_jsonl(
                record_dir / "logs" / "provider.raw.jsonl",
                [
                    {
                        "type": "octobench_process_timing",
                        "started_at_ms": 1000,
                        "ended_at_ms": 9000,
                    }
                ],
            )

            metrics = extract_opencode(record_dir, 8000)

            self.assertEqual(metrics.model_ms, 7000)
            self.assertEqual(metrics.tool_ms, 1000)
            self.assertEqual(metrics.busy_ms, 8000)

    def test_codex_counts_every_started_tool_execution_item(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            record_dir = Path(raw_tmp) / "run"
            _write_jsonl(
                record_dir / "logs" / "provider.raw.jsonl",
                [
                    {
                        "type": "item.started",
                        "item": {
                            "id": "file-1",
                            "type": "file_change",
                            "changes": [{"path": "a.py", "kind": "update"}],
                        },
                    },
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "file-1",
                            "type": "file_change",
                            "changes": [{"path": "a.py", "kind": "update"}],
                            "status": "completed",
                        },
                    },
                    {
                        "type": "item.started",
                        "item": {
                            "id": "mcp-1",
                            "type": "mcp_tool_call",
                            "arguments": {"path": "a.py"},
                        },
                    },
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "mcp-1",
                            "type": "mcp_tool_call",
                            "result": "ok",
                        },
                    },
                ],
            )

            metrics = extract_codex(record_dir, 1000)

            self.assertEqual(metrics.tool_calls, 2)
            self.assertEqual(metrics.repeat_calls, 0)

    def test_filler_echo_and_printf_require_pure_literals(self) -> None:
        for command in (
            "echo *",
            "echo ?",
            "echo [ab]",
            "echo $HOME",
            "echo `pwd`",
            "echo {a,b}",
            "echo hi | tee out",
            "printf hi > out",
            "echo hi; true",
            "echo hi && true",
            "echo hi || true",
        ):
            with self.subTest(command=command):
                self.assertFalse(is_filler_call("shell", {"command": command}))
        self.assertTrue(is_filler_call("shell", {"command": "echo '*'"}))
        self.assertTrue(is_filler_call("shell", {"command": "printf '%s\\n' literal"}))


class EfficiencyMathTest(unittest.TestCase):
    def _item(
        self,
        key: str,
        *,
        passed: bool,
        cost: float,
        wall_ms: int,
        busy_ms: int,
        tail_ms: int,
        calls: int,
        repeats: int,
        fillers: int,
        own_job_ms: int = 0,
        stuck_wait_ms: int = 0,
        longest_silent_gap_ms: int = 0,
    ) -> gold_scorecard.Item:
        efficiency = EfficiencyMetrics(
            wall_ms=wall_ms,
            model_ms=busy_ms,
            tool_ms=0,
            own_job_ms=own_job_ms,
            stuck_wait_ms=stuck_wait_ms,
            busy_ms=busy_ms,
            idle_ms=wall_ms - busy_ms,
            longest_silent_gap_ms=longest_silent_gap_ms,
            tail_ms=tail_ms,
            tool_calls=calls,
            repeat_calls=repeats,
            filler_calls=fillers,
        )
        return gold_scorecard.Item(
            key=key,
            kind="oneshot",
            sequence_id=None,
            passed=passed,
            judge=100,
            cost=cost,
            fresh_input=0,
            cache_read=0,
            output=0,
            reasoning=0,
            elapsed_ms=wall_ms,
            efficiency=efficiency,
        )

    def test_report_aggregate_math(self) -> None:
        items = [
            self._item(
                "a", passed=True, cost=3, wall_ms=1_800_000, busy_ms=900_000,
                tail_ms=1000, calls=2, repeats=1, fillers=0, own_job_ms=600_000,
                stuck_wait_ms=300_000, longest_silent_gap_ms=360_000,
            ),
            self._item(
                "b", passed=False, cost=1, wall_ms=1_800_000, busy_ms=900_000,
                tail_ms=3000, calls=2, repeats=0, fillers=1,
                longest_silent_gap_ms=100_000,
            ),
        ]

        self.assertEqual(gold_scorecard._cost_per_solve(items), 4)
        self.assertEqual(gold_scorecard._wall_time_per_solve(items), 3_600_000)
        self.assertEqual(gold_scorecard._burn_rate(items), 4)
        self.assertEqual(gold_scorecard._active_share(items), 0.5)
        self.assertEqual(gold_scorecard._idle_ms(items), 1_800_000)
        self.assertEqual(gold_scorecard._own_job_ms(items), 600_000)
        self.assertEqual(gold_scorecard._stuck_wait_ms(items), 300_000)
        self.assertEqual(gold_scorecard._silent_gap_stats(items), (360_000, 1))
        self.assertEqual(gold_scorecard._waste_share(items), 0.5)
        self.assertEqual(gold_scorecard._mean_tail_ms(items), 2000)

    def test_wall_time_per_solve_includes_failed_attempts(self) -> None:
        items = [
            self._item(
                "solved", passed=True, cost=1, wall_ms=600_000, busy_ms=300_000,
                tail_ms=0, calls=1, repeats=0, fillers=0,
            ),
            self._item(
                "failed", passed=False, cost=1, wall_ms=1_200_000, busy_ms=100_000,
                tail_ms=0, calls=1, repeats=0, fillers=0,
            ),
        ]

        self.assertEqual(gold_scorecard._wall_time_per_solve(items), 1_800_000)

    def test_geometric_relative_index_and_unknown_propagation(self) -> None:
        self.assertAlmostEqual(geometric_mean([0.5, 2.0]), 1.0)
        indexes, excluded = relative_indexes(
            {
                "a": {"one": 1.0, "two": 1.0},
                "b": {"one": 3.0, "two": 9.0},
            }
        )
        self.assertAlmostEqual(indexes["a"], math.sqrt(0.5 * 0.2))
        self.assertAlmostEqual(indexes["b"], math.sqrt(1.5 * 1.8))
        self.assertEqual(excluded, 0)

        unknown, excluded = relative_indexes(
            {"a": {"one": 1.0, "two": 1.0}, "b": {"one": 3.0, "two": None}}
        )
        self.assertIsNotNone(unknown["a"])
        self.assertIsNone(unknown["b"])
        self.assertEqual(excluded, 0)
        self.assertEqual(
            gold_scorecard._optional_summary([None], gold_scorecard._percent),
            "**UNKNOWN**",
        )

    def test_zero_values_are_known_and_excluded_from_relative_indexes(self) -> None:
        indexes, excluded = relative_indexes(
            {
                "a": {"zero": 0.0, "usable": 1.0},
                "b": {"zero": 0.0, "usable": 3.0},
            }
        )

        self.assertEqual(excluded, 1)
        self.assertEqual(indexes, {"a": 0.5, "b": 1.5})

        no_items, excluded = relative_indexes(
            {"a": {"zero": 0.0}, "b": {"zero": 0.0}}
        )
        self.assertEqual(excluded, 1)
        self.assertEqual(no_items, {"a": None, "b": None})

    def test_headline_is_first_efficiency_row_and_geometric_cost_time_mean(self) -> None:
        columns = [
            (
                "a",
                {
                    "r1": {
                        "shared": self._item(
                            "shared",
                            passed=True,
                            cost=1,
                            wall_ms=1000,
                            busy_ms=1000,
                            tail_ms=0,
                            calls=1,
                            repeats=0,
                            fillers=0,
                        )
                    }
                },
            ),
            (
                "b",
                {
                    "r1": {
                        "shared": self._item(
                            "shared",
                            passed=True,
                            cost=4,
                            wall_ms=4000,
                            busy_ms=4000,
                            tail_ms=0,
                            calls=1,
                            repeats=0,
                            fillers=0,
                        )
                    }
                },
            ),
        ]

        rows = gold_scorecard._metric_rows(columns)
        efficiency_rows = [row for row in rows if row[0].startswith("efficiency")]

        self.assertEqual(
            efficiency_rows[0][0],
            "efficiency-only headline — matched work cost/time index",
        )
        self.assertEqual(
            efficiency_rows[0][1],
            ["0.40 (0.40–0.40)", "1.60 (1.60–1.60)"],
        )
        rows_by_name = dict(rows)
        self.assertEqual(
            rows_by_name[
                "efficiency — matched work — zero-cost items excluded from relative index"
            ],
            ["0 (0–0)", "0 (0–0)"],
        )
        self.assertEqual(gold_scorecard._headline_index(0.5, 2.0), 1.0)
        self.assertIsNone(gold_scorecard._headline_index(None, 2.0))


if __name__ == "__main__":
    unittest.main()

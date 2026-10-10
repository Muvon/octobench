from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cli import main as main_cli
from providers.base import ProviderRunResult
from runners.executor import CASE_TIMEOUT_MARKER
from scripts.rerun_failed import infra_failed


class _Executor:
    case_timeout_s = None

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.closed = False

    def container_workspace(self) -> str:
        return str(self.workspace)

    def workspace_host_path(self) -> Path:
        return self.workspace

    def close(self) -> None:
        self.closed = True


class _TimeoutProvider:
    def run_task(self, **_kwargs) -> ProviderRunResult:
        return ProviderRunResult(
            stdout="partial work",
            stderr=f"stalled\n{CASE_TIMEOUT_MARKER} 2700s",
            exit_code=124,
            elapsed_ms=2_700_000,
            input_tokens=1_000_000,
            cached_input_tokens=500_000,
            output_tokens=100_000,
            reasoning_tokens=50_000,
            total_tokens=1_650_000,
            aux_input_tokens=100_000,
            aux_output_tokens=50_000,
            aux_cost_usd=0.36,
        )


class MainTimeoutProviderHealthTest(unittest.TestCase):
    def _run_timeout(self, probe_result: tuple[bool, str]) -> tuple[dict, list[str]]:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            cases_dir = tmp / "cases" / "timeout_case"
            cases_dir.mkdir(parents=True)
            (cases_dir / "case.yaml").write_text(
                "id: timeout_case\ninstruction: test timeout\n",
                encoding="utf-8",
            )
            out_dir = tmp / "results"
            workspace = tmp / "workspace"
            workspace.mkdir()
            executor = _Executor(workspace)
            logs: list[str] = []
            script_result = {
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "elapsed_ms": 1,
            }
            argv = [
                "cli.main",
                "run",
                "--cases",
                str(tmp / "cases"),
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
                patch.dict(os.environ, {"OCTOBENCH_SEAL_NETWORK": "0"}),
                patch.object(main_cli, "enforce_clean_bench"),
                patch.object(main_cli, "get_provider", return_value=_TimeoutProvider()),
                patch.object(main_cli, "make_executor", return_value=executor),
                patch.object(main_cli, "run_case_script", return_value=script_result),
                patch.object(main_cli, "install_guardrails"),
                patch.object(main_cli, "snapshot_files", return_value={}),
                patch.object(main_cli, "clean_workspace"),
                patch.object(
                    main_cli,
                    "probe_provider_health",
                    return_value=probe_result,
                ) as probe,
                patch.object(main_cli.time, "strftime", return_value="20261007-040000"),
                patch.object(
                    main_cli,
                    "log",
                    side_effect=lambda message, *_args: logs.append(message),
                ),
            ):
                with self.assertRaisesRegex(SystemExit, "1"):
                    main_cli.main()

            self.assertTrue(executor.closed)
            probe.assert_called_once()
            record = json.loads(
                (out_dir / "20261007-040000" / "results.json").read_text()
            )["results"][0]
            return record, logs

    def test_unhealthy_probe_marks_timeout_as_retryable_infra(self) -> None:
        record, logs = self._run_timeout((False, "quota exhausted"))

        self.assertTrue(record["infra_failed"])
        self.assertFalse(record["timed_out"])
        self.assertEqual(record["provider_unavailable"], "quota exhausted")
        self.assertEqual(record["judge"]["reasoning"], "provider unavailable")
        self.assertEqual(record["cost_usd"], 2.55)
        self.assertTrue(infra_failed(record))
        self.assertTrue(
            any("PROVIDER-UNAVAILABLE case=timeout_case" in line for line in logs)
        )

    def test_healthy_probe_keeps_non_retryable_timeout(self) -> None:
        record, logs = self._run_timeout((True, ""))

        self.assertFalse(record["infra_failed"])
        self.assertTrue(record["timed_out"])
        self.assertNotIn("provider_unavailable", record)
        self.assertEqual(record["judge"]["reasoning"], "case timeout")
        self.assertEqual(record["cost_usd"], 2.55)
        self.assertFalse(infra_failed(record))
        self.assertTrue(any("CASE-TIMEOUT case=timeout_case" in line for line in logs))


if __name__ == "__main__":
    unittest.main()

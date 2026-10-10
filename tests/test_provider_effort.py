from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from providers.codex import CodexProvider
from providers.octomind import OctomindProvider


class RecordingExecutor:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.commands: list[list[str]] = []

    def container_workspace(self) -> str:
        return str(self.workspace)

    def workspace_host_path(self) -> Path:
        return self.workspace

    def octomind_config_path(self) -> str:
        return "/cfg/octomind.toml"

    def run(self, cmd, **_kwargs):
        self.commands.append(list(cmd))
        return SimpleNamespace(stdout="", stderr="", exit_code=0)


def _command(provider, reasoning_effort: str | None) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp, patch.dict(
        os.environ, {"OCTOBENCH_CONTEXT_WINDOW": "200000"}
    ):
        executor = RecordingExecutor(Path(tmp))
        provider.run_task(
            prompt="task",
            workdir=tmp,
            provider_model="model",
            session_name="s",
            executor=executor,
            reasoning_effort=reasoning_effort,
        )
        return executor.commands[0]


class ProviderEffortTest(unittest.TestCase):
    def test_codex_passes_effort_as_config_override(self) -> None:
        cmd = _command(CodexProvider(), "low")
        self.assertIn('model_reasoning_effort="low"', cmd)
        self.assertEqual(cmd[cmd.index('model_reasoning_effort="low"') - 1], "-c")

    def test_octomind_passes_effort_as_config_override(self) -> None:
        cmd = _command(OctomindProvider(), "medium")
        self.assertEqual(cmd[-2:], ["-c", "model.reasoning_effort=medium"])

    def test_unset_effort_leaves_client_default(self) -> None:
        for provider in (CodexProvider(), OctomindProvider()):
            self.assertFalse(any("reasoning_effort" in arg for arg in _command(provider, None)))


if __name__ == "__main__":
    unittest.main()

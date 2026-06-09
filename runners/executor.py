from __future__ import annotations

import os
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

# Host environment variables carrying provider/tool auth. The Docker executor
# forwards these (by name, so values stay off the command line) into the
# container, so agents authenticate with the same credentials as the host.
AUTH_ENV_KEYS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "DEEPSEEK_API_KEY",
    "MOONSHOT_API_KEY",
    "ZAI_API_KEY",
    "MINIMAX_API_KEY",
    "GROQ_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "OCTOHUB_API_KEY",
    "OCTOHUB_API_URL",
    "BRAVE_API_KEY",
    "TAVILY_API_KEY",
]


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int


class Executor(ABC):
    """
    Abstracts WHERE a command runs. The host flow runs commands as local
    subprocesses; the docker flow runs them via `docker exec` inside a
    per-run container. Providers and case scripts go through this so the
    orchestration (snapshot/judge/scoring) stays identical for both.
    """

    @abstractmethod
    def run(
        self,
        argv: List[str],
        env_overrides: Optional[Dict[str, str]] = None,
        input_text: Optional[str] = None,
    ) -> ExecResult:
        """Run argv (capturing output) for provider/agent invocations."""

    @abstractmethod
    def bash_script(
        self,
        name: str,
        verbosity: str,
        log_fn: Callable[[str, str, str], None],
        extra_env: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """Run a case script by name (setup.sh/quality.sh/validate.sh), streaming logs."""

    @abstractmethod
    def container_workspace(self) -> str:
        """Path of the workspace as seen by the command (host path or /workspace)."""

    @abstractmethod
    def workspace_host_path(self) -> Path:
        """Host path of the workspace (used to snapshot files for evidence)."""

    @abstractmethod
    def octomind_config_path(self) -> str:
        """OCTOMIND_CONFIG_PATH value valid in this executor's environment."""

    def close(self) -> None:
        pass


def _stream(proc: subprocess.Popen, name: str, verbosity: str, log_fn) -> Dict:
    stdout_lines: List[str] = []
    stderr_lines: List[str] = []

    def pump(stream, target: List[str], label: str) -> None:
        for raw in iter(stream.readline, ""):
            target.append(raw)
            if verbosity != "quiet":
                line = raw.rstrip("\n")
                if line:
                    log_fn(name, label, line)
        stream.close()

    t_out = threading.Thread(target=pump, args=(proc.stdout, stdout_lines, "stdout"), daemon=True)
    t_err = threading.Thread(target=pump, args=(proc.stderr, stderr_lines, "stderr"), daemon=True)
    t_out.start()
    t_err.start()
    code = proc.wait()
    t_out.join()
    t_err.join()
    return {"exit_code": code, "stdout": "".join(stdout_lines), "stderr": "".join(stderr_lines)}


class HostExecutor(Executor):
    def __init__(self, workspace: Path, case_dir: Path, octomind_config: Path):
        self._ws = Path(workspace).resolve()
        self._case_dir = Path(case_dir).resolve()
        self._octomind_config = str(Path(octomind_config).resolve())

    def run(self, argv, env_overrides=None, input_text=None) -> ExecResult:
        env = os.environ.copy()
        if env_overrides:
            env.update({k: str(v) for k, v in env_overrides.items()})
        proc = subprocess.run(
            argv,
            cwd=str(self._ws),
            capture_output=True,
            text=True,
            input=input_text,
            env=env,
        )
        return ExecResult(proc.stdout or "", proc.stderr or "", proc.returncode)

    def bash_script(self, name, verbosity, log_fn, extra_env=None) -> Dict:
        script_path = self._case_dir / name
        if not script_path.exists():
            return {"exit_code": 0, "stdout": "", "stderr": "", "elapsed_ms": 0}
        env = {**os.environ, "CASE_DIR": str(self._case_dir), "WORKDIR": str(self._ws)}
        if extra_env:
            env.update(extra_env)
        start = time.time()
        proc = subprocess.Popen(
            ["bash", str(script_path)],
            cwd=str(self._ws),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        result = _stream(proc, name, verbosity, log_fn)
        result["elapsed_ms"] = int((time.time() - start) * 1000)
        return result

    def container_workspace(self) -> str:
        return str(self._ws)

    def workspace_host_path(self) -> Path:
        return self._ws

    def octomind_config_path(self) -> str:
        return self._octomind_config


class DockerExecutor(Executor):
    """
    Runs each case in its own container. The workspace is a host dir bind-mounted
    at /workspace, the case dir at /case (ro), and the octomind config at
    /cfg/octomind.toml (ro). Host auth is forwarded via env vars (+ codex auth
    file mount). Snapshots still happen on the host via the mounted workspace.
    """

    CASE = "/case"
    CFG = "/cfg/octomind.toml"

    def __init__(
        self,
        image: str,
        workspace: Path,
        case_dir: Path,
        octomind_config: Path,
        container_name: str,
        workdir: str = "/workspace",
        platform: Optional[str] = None,
        mount_workspace: bool = True,
        mount_case: bool = True,
    ):
        self.image = image
        self._ws = Path(workspace).resolve()
        self._case_dir = Path(case_dir).resolve()
        self._octomind_config = Path(octomind_config).resolve()
        self.name = container_name
        self._workdir = workdir
        self._platform = platform
        self._mount_workspace = mount_workspace
        self._mount_case = mount_case
        self._started = False

    def _ensure(self) -> None:
        if self._started:
            return
        env_args: List[str] = []
        for k in AUTH_ENV_KEYS:
            if os.environ.get(k) is not None:
                env_args += ["-e", k]  # pass-through by name; value from host env
        for k, v in {
            "OCTOMIND_CONFIG_PATH": self.CFG,
            "CASE_DIR": self.CASE,
            "WORKDIR": self._workdir,
            "HOME": "/root",
            # Containers run as root; claude refuses --dangerously-skip-permissions
            # as root unless this sandbox marker is set (it is sandboxed here).
            "IS_SANDBOX": "1",
        }.items():
            env_args += ["-e", f"{k}={v}"]

        mounts = ["-v", f"{self._octomind_config}:{self.CFG}:ro"]
        # repo-in-image mode (SWE-bench): the repo lives inside the image at
        # `workdir`, so no host workspace/case is mounted.
        if self._mount_workspace:
            mounts += ["-v", f"{self._ws}:{self._workdir}"]
        if self._mount_case:
            mounts += ["-v", f"{self._case_dir}:{self.CASE}:ro"]
        codex_auth = Path.home() / ".codex" / "auth.json"
        if codex_auth.exists():
            mounts += ["-v", f"{codex_auth}:/root/.codex/auth.json:ro"]

        platform_args = ["--platform", self._platform] if self._platform else []
        cmd = [
            "docker", "run", "-d", *platform_args, "--name", self.name, "-w", self._workdir,
            *mounts, *env_args, self.image, "sleep", "infinity",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"docker run failed for {self.name}: {proc.stderr.strip()}")
        self._started = True

    def run(self, argv, env_overrides=None, input_text=None) -> ExecResult:
        self._ensure()
        exec_cmd = ["docker", "exec", "-i", "-w", self._workdir]
        if env_overrides:
            for k, v in env_overrides.items():
                exec_cmd += ["-e", f"{k}={v}"]
        exec_cmd += [self.name, *argv]
        proc = subprocess.run(exec_cmd, capture_output=True, text=True, input=input_text)
        return ExecResult(proc.stdout or "", proc.stderr or "", proc.returncode)

    def bash_script(self, name, verbosity, log_fn, extra_env=None) -> Dict:
        self._ensure()
        # Probe existence so a missing optional script is a no-op (matches host).
        probe = subprocess.run(
            ["docker", "exec", self.name, "test", "-f", f"{self.CASE}/{name}"],
            capture_output=True, text=True,
        )
        if probe.returncode != 0:
            return {"exit_code": 0, "stdout": "", "stderr": "", "elapsed_ms": 0}
        exec_cmd = ["docker", "exec", "-w", self._workdir]
        if extra_env:
            for k, v in extra_env.items():
                exec_cmd += ["-e", f"{k}={v}"]
        exec_cmd += [self.name, "bash", f"{self.CASE}/{name}"]
        start = time.time()
        proc = subprocess.Popen(
            exec_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        result = _stream(proc, name, verbosity, log_fn)
        result["elapsed_ms"] = int((time.time() - start) * 1000)
        return result

    def container_workspace(self) -> str:
        return self._workdir

    def workspace_host_path(self) -> Path:
        return self._ws

    def octomind_config_path(self) -> str:
        return self.CFG

    def close(self) -> None:
        if self._started:
            subprocess.run(["docker", "rm", "-f", self.name], capture_output=True, text=True)
            self._started = False

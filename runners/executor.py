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
# Prepared once by scripts/prepare_caches.sh and mounted into every container, so
# no run pays to fetch a tap or an embedding model — and no run depends on
# fetching one, which a sealed container cannot do (neither github nor
# huggingface is on the egress allowlist). Env vars override for one-off runs.
DEFAULT_CACHE_ROOT = Path.home() / ".cache" / "octobench"

AUTH_ENV_KEYS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "DEEPSEEK_API_KEY",
    "MOONSHOT_API_KEY",
    "ZAI_API_KEY",
    "ZAI_API_URL",
    "MINIMAX_API_KEY",
    "GROQ_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "OCTOHUB_API_KEY",
    "OCTOHUB_API_URL",
    "OLLAMA_API_KEY",
    "OLLAMA_API_URL",
    # Not auth: forwarded so an instrumented run can surface the agent's debug
    # tracing in provider.stderr.log. Absent from the host env in normal runs.
    "RUST_LOG",
    "OCTOMIND_AGENT",
    "BRAVE_API_KEY",
    "TAVILY_API_KEY",
    "ALIBABA_API_KEY",
    "ALIBABA_API_URL",
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

    # Per-case wall-clock budget for `run()` calls (the agent invocation), set by
    # the orchestrator from the case's `timeout_minutes`. Enforcing it INSIDE the
    # run (instead of an external `timeout` on the whole harness) means a timeout
    # still writes an infra-marked record and the container still gets torn down —
    # an external kill leaves neither.
    case_timeout_s: Optional[int] = None

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
        try:
            proc = subprocess.run(
                argv,
                cwd=str(self._ws),
                capture_output=True,
                text=True,
                input=input_text,
                env=env,
                timeout=self.case_timeout_s,
            )
        except subprocess.TimeoutExpired as e:
            # TimeoutExpired output is bytes even in text mode.
            stdout = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode(errors="replace")
            stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr or b"").decode(errors="replace")
            return ExecResult(
                stdout,
                stderr + f"\noctobench: case timeout after {self.case_timeout_s}s",
                124,
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

        # octobench: client session state, kept on the HOST beside the workspace.
        # Agents write their sessions inside the container, which is fine while a
        # sequence runs (that is what `-r`/`--session` resume reads) but the
        # container is removed at sequence end and takes the evidence with it —
        # compaction summaries, fold points, what the agent believed it had done.
        # Mounting it out costs nothing and makes a finished run investigable.
        # claude and codex are deliberately absent: their state dirs already
        # receive individual auth FILE mounts below, and mounting the parent
        # directory would shadow them.
        state_root = self._ws.parent / "state"
        for sub, dest, env_var in (
            ("octomind", "/octobench-state/octomind", "OCTOMIND_DATA_DIR"),
            ("opencode", "/root/.local/share/opencode", None),
        ):
            host_dir = state_root / sub
            host_dir.mkdir(parents=True, exist_ok=True)
            mounts += ["-v", f"{host_dir}:{dest}"]
            if env_var:
                env_args += ["-e", f"{env_var}={dest}"]
        # octobench: optional octomind binary override (built-from-ref),
        # mounted over the baked binary so one image serves multiple refs.
        _ob = os.environ.get("OCTOMIND_BIN")
        if _ob and Path(_ob).exists():
            mounts += ["-v", f"{Path(_ob).resolve()}:/usr/local/bin/octomind:ro"]
        # octobench: shared model cache, pre-seeded on the host. Octomind pulls its
        # embedding model from huggingface at startup — measured at 32s before the
        # first model request, and huggingface is NOT on the seal allowlist, so in a
        # sealed run that fetch is blocked and paid for as retry/timeout on every
        # session. Seeding it once removes both, and keeps the download out of the
        # numbers we are actually measuring.
        # Two caches, both fetched at startup and both off the allowlist:
        # huggingface (88M, octomind's own embed model) and octolib/fastembed
        # (1.2G, nomic + jina code embeddings).
        _mc = os.environ.get("OCTOBENCH_MODEL_CACHE") or (DEFAULT_CACHE_ROOT / "models")
        if _mc:
            _mc_root = Path(_mc).resolve()
            for _sub, _dest in (
                ("huggingface", "/root/.cache/huggingface"),
                ("octolib", "/root/.cache/octolib"),
            ):
                if (_mc_root / _sub).is_dir():
                    mounts += ["-v", f"{_mc_root / _sub}:{_dest}"]
        # octobench: octofs override — octomind's file/shell tool server, pinned in
        # the image but swappable to compare tool-server versions on one image.
        _fb = os.environ.get("OCTOFS_BIN")
        if _fb and Path(_fb).exists():
            mounts += ["-v", f"{Path(_fb).resolve()}:/usr/local/bin/octofs:ro"]
        # octobench: same override for codex (new models can require a newer CLI
        # than the one baked in the image, e.g. gpt-5.6-sol needs >= 0.145.0).
        _cb = os.environ.get("CODEX_BIN")
        if _cb and Path(_cb).exists():
            mounts += ["-v", f"{Path(_cb).resolve()}:/usr/local/bin/codex:ro"]
        # octobench: opencode is not baked into the image — binary and its
        # provider config (custom ollama endpoint) are mounted when set.
        _oc = os.environ.get("OPENCODE_BIN")
        if _oc and Path(_oc).exists():
            mounts += ["-v", f"{Path(_oc).resolve()}:/usr/local/bin/opencode:ro"]
        _occ = os.environ.get("OPENCODE_CONFIG_JSON")
        if _occ and Path(_occ).exists():
            mounts += ["-v", f"{Path(_occ).resolve()}:"
                             "/root/.config/opencode/opencode.json:ro"]
        # octobench: staged muvon tap mounted over the container tap cache so
        # role edits under test reach fresh containers without publishing.
        # Read-only is safe: octomind's silent `git pull` on it fails and the
        # staged copy is used as-is.
        _tap = os.environ.get("OCTOMIND_TAP_CACHE") or (DEFAULT_CACHE_ROOT / "tap")
        if _tap and Path(_tap).is_dir():
            mounts += ["-v", f"{Path(_tap).resolve()}:"
                             "/root/.local/share/octomind/taps/muvon/octomind-tap:ro"]
        # octolib embedding-model cache, warmed once on the host — mounted
        # read-only so octocode loads models from cache instead of fetching
        # them from HF inside octomind's stdin-init timeout. Legacy path: skip
        # when the model-cache block above already mounted /root/.cache/octolib
        # (docker hard-errors on a duplicate mount point).
        _oc_cache = Path(os.environ.get("OCTOLIB_CACHE",
                                        str(Path.home() / "octolib-cache")))
        octolib_mounted = any("/root/.cache/octolib" in m for m in mounts)
        if not octolib_mounted and _oc_cache.is_dir() and any(_oc_cache.iterdir()):
            mounts += ["-v", f"{_oc_cache.resolve()}:/root/.cache/octolib:ro"]
        # repo-in-image mode (SWE-bench): the repo lives inside the image at
        # `workdir`, so no host workspace/case is mounted.
        if self._mount_workspace:
            mounts += ["-v", f"{self._ws}:{self._workdir}"]
        if self._mount_case:
            mounts += ["-v", f"{self._case_dir}:{self.CASE}:ro"]
        # Tool login credentials (NOT API keys), mounted read-WRITE: codex ->
        # ~/.codex/auth.json; claude -> ~/.claude/.credentials.json (Linux; on macOS
        # claude uses the Keychain, so nothing to mount there).
        #
        # MUST be writable. These are OAuth logins: the agent refreshes the short-lived
        # access token mid-run, and the provider ROTATES the refresh token on use
        # (the old one is invalidated server-side). With a :ro mount the agent gets the
        # new token but can't save it back, so the run invalidates the host login →
        # every later run (and the user's own session) gets a 401. Read-write lets the
        # refreshed token persist. Safe here because agent runs are sequential — no two
        # containers write the same credential file at once.
        codex_auth = Path.home() / ".codex" / "auth.json"
        if codex_auth.exists():
            mounts += ["-v", f"{codex_auth}:/root/.codex/auth.json:rw"]
        claude_creds = Path.home() / ".claude" / ".credentials.json"
        if claude_creds.exists():
            mounts += ["-v", f"{claude_creds}:/root/.claude/.credentials.json:rw"]

        platform_args = ["--platform", self._platform] if self._platform else []
        # NET_ADMIN lets cli.main seal the container's egress for the agent phase
        # (see seal_network); without it the agent can reach the upstream fix.
        net_args = ["--cap-add=NET_ADMIN"] if os.environ.get("OCTOBENCH_SEAL_NETWORK") == "1" else []
        cmd = [
            "docker", "run", "-d", *platform_args, *net_args,
            "--name", self.name, "-w", self._workdir,
            *mounts, *env_args, self.image, "sleep", "infinity",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"docker run failed for {self.name}: {proc.stderr.strip()}")
        self._started = True

    def run(self, argv, env_overrides=None, input_text=None) -> ExecResult:
        self._ensure()
        # Attach stdin only when the caller supplies input. An unconditional
        # `docker exec -i` inherits a detached tmux launcher's terminal and can
        # stop on SIGTTIN before the agent starts (for example, guardrail setup).
        exec_cmd = ["docker", "exec"]
        if input_text is not None:
            exec_cmd.append("-i")
        exec_cmd += ["-w", self._workdir]
        if env_overrides:
            for k, v in env_overrides.items():
                exec_cmd += ["-e", f"{k}={v}"]
        exec_cmd += [self.name, *argv]
        try:
            proc = subprocess.run(
                exec_cmd, capture_output=True, text=True, input=input_text,
                timeout=self.case_timeout_s,
            )
        except subprocess.TimeoutExpired as e:
            # The killed `docker exec` client does not stop the process inside
            # the container; close() (docker rm -f) reaps it with the container.
            stdout = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode(errors="replace")
            stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr or b"").decode(errors="replace")
            return ExecResult(
                stdout,
                stderr + f"\noctobench: case timeout after {self.case_timeout_s}s",
                124,
            )
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

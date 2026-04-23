from __future__ import annotations

import json
import os
import re
import subprocess
import time
from typing import Dict, Optional

from .base import RunResult


def _extract_tokens(text: str, regex: Optional[str]) -> Optional[int]:
    if not regex:
        return None
    m = re.search(regex, text)
    if not m:
        return None
    try:
        value = m.group(1)
        value = value.replace(",", "").replace("_", "")
        return int(value)
    except Exception:
        return None


def _resolve_executable(cmd0: str, env: Dict[str, str]) -> str:
    # If already a path, use as-is.
    if os.path.sep in cmd0:
        return cmd0
    path_value = env.get("PATH", os.environ.get("PATH", ""))
    for raw_dir in path_value.split(os.pathsep):
        if not raw_dir:
            continue
        expanded = os.path.expandvars(os.path.expanduser(raw_dir))
        candidate = os.path.join(expanded, cmd0)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return cmd0


def run_cli(prompt: str, workdir: str, meta: Dict) -> RunResult:
    command = meta.get("command")
    if not command:
        raise ValueError("setup missing command")

    # Write prompt to temp file for CLI tools that accept file input
    io_dir = os.path.abspath(meta.get("io_dir", workdir))
    os.makedirs(io_dir, exist_ok=True)
    io_tag = str(meta.get("io_tag", time.time_ns()))
    prompt_file = os.path.join(io_dir, f"_prompt_{io_tag}.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt)
    output_file = os.path.join(io_dir, f"_output_{io_tag}.txt")

    repo_root = os.path.abspath(meta.get("repo_root", os.getcwd()))

    def _subst(arg: str) -> str:
        return (
            arg.replace("{prompt_file}", prompt_file)
            .replace("{output_file}", output_file)
            .replace("{workdir}", workdir)
            .replace("{repo_root}", repo_root)
            .replace("{provider_model}", str(meta.get("provider_model", "")))
            .replace("{benchmark_model}", str(meta.get("benchmark_model", "")))
            .replace("{prompt}", prompt)
        )

    cmd = [_subst(a) for a in command]

    start = time.time()
    stdin_prompt = meta.get("stdin_prompt", False)
    env = {**os.environ, **meta.get("env", {})}
    env = {k: _subst(v) if isinstance(v, str) else v for k, v in env.items()}
    if cmd:
        cmd[0] = _resolve_executable(cmd[0], env)

    try:
        proc = subprocess.run(
            cmd,
            cwd=workdir,
            capture_output=True,
            text=True,
            input=prompt if stdin_prompt else None,
            env=env,
        )
        proc_stdout = proc.stdout or ""
        proc_stderr = proc.stderr or ""
        proc_code = proc.returncode
    except OSError as e:
        elapsed_ms = int((time.time() - start) * 1000)
        err = f"Failed to execute command: {' '.join(cmd)} ({e.__class__.__name__}: {e})"
        return RunResult(
            stdout="",
            stderr=err,
            exit_code=126 if isinstance(e, PermissionError) else 1,
            elapsed_ms=elapsed_ms,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            cached_input_tokens=None,
        )
    elapsed_ms = int((time.time() - start) * 1000)

    # If tool writes the final message to output_file, prefer that.
    stdout = ""
    if os.path.exists(output_file):
        try:
            with open(output_file, encoding="utf-8") as f:
                stdout = f.read()
        except Exception:
            stdout = proc_stdout
    else:
        stdout = proc_stdout
    stderr = proc_stderr

    input_tokens = None
    output_tokens = None
    total_tokens = None
    cached_input_tokens = None
    last_agent_message = None

    # If tool emits JSONL events, parse usage and assistant output.
    # Supports Codex event schema and Octomind JSONL schema.
    if meta.get("json_events"):
        for line in proc_stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            usage = obj.get("usage")
            if isinstance(usage, dict):
                input_tokens = usage.get("input_tokens", input_tokens)
                cached_input_tokens = usage.get("cached_input_tokens", cached_input_tokens)
                output_tokens = usage.get("output_tokens", output_tokens)
                if input_tokens is not None and output_tokens is not None:
                    total_tokens = input_tokens + output_tokens

            # Octomind JSONL cost message.
            if obj.get("type") == "cost":
                raw_in = obj.get("input_tokens")
                raw_out = obj.get("output_tokens")
                raw_cached = obj.get("cache_read_tokens", obj.get("cached_tokens"))
                raw_total = obj.get("session_tokens")
                try:
                    if raw_in is not None:
                        input_tokens = int(raw_in)
                    if raw_out is not None:
                        output_tokens = int(raw_out)
                    if raw_cached is not None:
                        cached_input_tokens = int(raw_cached)
                    if raw_total is not None:
                        total_tokens = int(raw_total)
                except Exception:
                    pass

            item = obj.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                last_agent_message = item.get("text", last_agent_message)
            # Octomind JSONL assistant message.
            if obj.get("type") == "assistant":
                content = obj.get("content")
                if isinstance(content, str) and content.strip():
                    last_agent_message = content
        if last_agent_message:
            stdout = last_agent_message

    token_regexes = meta.get("token_regexes", {})
    combined = stdout + "\n" + stderr + "\n" + proc_stdout
    if input_tokens is None:
        input_tokens = _extract_tokens(combined, token_regexes.get("input"))
    if output_tokens is None:
        output_tokens = _extract_tokens(combined, token_regexes.get("output"))
    if total_tokens is None:
        total_tokens = _extract_tokens(combined, token_regexes.get("total"))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    return RunResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=proc_code,
        elapsed_ms=elapsed_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cached_input_tokens=cached_input_tokens,
    )

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Optional

from providers.base import Provider, ProviderRunResult, shared_system_prompt

if TYPE_CHECKING:
    from runners.executor import Executor


class CodexProvider(Provider):
    name = "codex"

    def __init__(self) -> None:
        # thread id -> cumulative (input, cached, output) reported so far. The
        # long-run runner keeps one provider instance per sequence, which is
        # what makes the per-turn delta below possible.
        self._thread_usage: dict[str, tuple[int, int, int]] = {}

    def run_task(
        self,
        prompt: str,
        workdir: str,
        provider_model: str,
        session_name: str,
        executor: "Executor",
        resume_session_id: Optional[str] = None,
    ) -> ProviderRunResult:
        # Paths must be valid inside the executor's environment (host cwd or the
        # container's /workspace); the result file is read back via the host mount.
        ws = executor.container_workspace()
        out_name = f"_provider_output_{session_name}.txt"
        output_file = f"{ws}/{out_name}"
        # Index at which `-c` overrides are spliced in: they must follow the
        # subcommand (and its session-id positional) to bind to it.
        opts_at = 4 if resume_session_id else 2
        if resume_session_id:
            # `codex exec resume <SESSION_ID>` continues a prior session.
            cmd = [
                "codex",
                "exec",
                "resume",
                resume_session_id,
                "--json",
                "-m",
                provider_model,
                # `resume` takes neither -C nor -s. The executor already runs it
                # with the workspace as cwd; the sandbox mode has to come in as
                # the config key -s would have set (same value as turn 1).
                "-c",
                'sandbox_mode="danger-full-access"',
                "--skip-git-repo-check",
                "--output-last-message",
                output_file,
                "-",
            ]
        else:
            cmd = [
                "codex",
                "exec",
                "--json",
                "-m",
                provider_model,
                "-C",
                ws,
                # danger-full-access (not workspace-write): codex's sandboxed modes wrap
                # every shell command in bubblewrap (bwrap), which isn't present and can't
                # run in the unprivileged container — so commands fail before starting. The
                # container is already the isolation boundary (like claude's IS_SANDBOX=1),
                # so we let codex run commands directly.
                "-s",
                "danger-full-access",
                "--skip-git-repo-check",
                "--output-last-message",
                output_file,
                "-",
            ]

        # Clean-bench mode: same shared prompt as every other client. Codex has no
        # web tool unless `--search` is passed, which it never is here.
        system_prompt = shared_system_prompt()
        if system_prompt:
            cmd[opts_at:opts_at] = ["-c", f"instructions={json.dumps(system_prompt)}"]

        start = time.time()
        proc = executor.run(cmd, input_text=prompt)
        elapsed_ms = int((time.time() - start) * 1000)

        stdout = ""
        host_output = executor.workspace_host_path() / out_name
        if host_output.exists():
            try:
                stdout = host_output.read_text(encoding="utf-8").strip()
            except Exception:
                stdout = (proc.stdout or "").strip()
        else:
            stdout = (proc.stdout or "").strip()

        # Raw `turn.completed.usage` counters, as codex reports them: input
        # INCLUDES cached, and every number is a RUNNING TOTAL for the thread —
        # a resumed turn restates the whole thread's usage. Measured: three
        # turns on one thread reported 28.1k / 42.7k / 57.3k input while each
        # trailing turn was trivial. They are converted to per-turn deltas below;
        # without that a 5-turn sequence would bill turn 1 five times.
        raw_input_total: Optional[int] = None
        raw_cached_total: Optional[int] = None
        raw_output_total: Optional[int] = None
        input_tokens: Optional[int] = None
        cached_input_tokens: Optional[int] = None
        output_tokens: Optional[int] = None
        total_tokens: Optional[int] = None
        session_id: Optional[str] = resume_session_id
        assistant_messages: list[str] = []
        tool_intents: list[str] = []
        tool_results: list[str] = []

        def _compact_text(value: Any, limit: int = 180) -> str:
            if value is None:
                return ""
            if isinstance(value, (dict, list)):
                text = json.dumps(value, ensure_ascii=True)
            else:
                text = str(value)
            text = " ".join(text.split())
            if len(text) > limit:
                return text[: limit - 3] + "..."
            return text

        def _tool_summary(item: dict[str, Any]) -> Optional[str]:
            item_type = str(item.get("type", "")).strip()
            if not item_type:
                return None
            type_lower = item_type.lower()
            if (
                "tool" not in type_lower
                and "command" not in type_lower
                and "function" not in type_lower
            ):
                return None

            name = (
                item.get("name")
                or item.get("tool_name")
                or item.get("function_name")
                or item.get("tool")
                or item_type
            )
            args = (
                item.get("arguments")
                or item.get("input")
                or item.get("params")
                or item.get("command")
                or item.get("cmd")
            )
            name_text = _compact_text(name, limit=60)
            args_text = _compact_text(args, limit=180)
            if args_text:
                return f"{name_text}: {args_text}"
            return name_text

        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            usage = obj.get("usage")
            if isinstance(usage, dict):
                raw_input_total = usage.get("input_tokens", raw_input_total)
                raw_cached_total = usage.get("cached_input_tokens", raw_cached_total)
                raw_output_total = usage.get("output_tokens", raw_output_total)
            # Extract session ID for multi-turn resumption. Codex 0.146 names it
            # thread_id on the `thread.started` event; older builds used
            # session_id. Without this the id stays None and every long-run turn
            # silently starts a fresh session.
            raw_session_id = (
                obj.get("thread_id") or obj.get("session_id") or obj.get("session")
            )
            if isinstance(raw_session_id, str):
                session_id = raw_session_id
            item = obj.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    msg = text.strip()
                    stdout = msg
                    assistant_messages.append(_compact_text(msg, limit=360))
            if isinstance(item, dict):
                summary = _tool_summary(item)
                if summary:
                    item_type = str(item.get("type", "")).lower()
                    if "result" in item_type:
                        tool_results.append(summary)
                    else:
                        tool_intents.append(summary)

        # Cumulative -> per-turn. The baseline is what this thread had already
        # reported before this invocation; a fresh thread starts at zero.
        if raw_input_total is not None:
            base_in, base_cached, base_out = self._thread_usage.get(
                session_id or "", (0, 0, 0)
            )
            self._thread_usage[session_id or ""] = (
                raw_input_total,
                raw_cached_total or 0,
                raw_output_total or 0,
            )
            delta_in = max(raw_input_total - base_in, 0)
            cached_input_tokens = max((raw_cached_total or 0) - base_cached, 0)
            output_tokens = max((raw_output_total or 0) - base_out, 0)
            # Canonical semantics: input excludes cached.
            input_tokens = max(delta_in - cached_input_tokens, 0)
            total_tokens = input_tokens + cached_input_tokens + output_tokens

        # Keep evidence compact and bounded.
        assistant_messages = assistant_messages[-12:]
        tool_intents = tool_intents[-24:]
        tool_results = tool_results[-24:]

        return ProviderRunResult(
            stdout=stdout,
            stderr=(proc.stderr or "").strip(),
            exit_code=proc.exit_code,
            elapsed_ms=elapsed_ms,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=None,
            total_tokens=total_tokens,
            session_id=session_id,
            provider_trace={
                "assistant_messages": assistant_messages,
                "tool_intents": tool_intents,
                "tool_results": tool_results,
            },
            raw_output=proc.stdout or "",
        )


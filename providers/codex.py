from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Optional

from providers.base import Provider, ProviderRunResult

if TYPE_CHECKING:
    from runners.executor import Executor


class CodexProvider(Provider):
    name = "codex"

    def run_task(
        self,
        prompt: str,
        workdir: str,
        provider_model: str,
        session_name: str,
        executor: "Executor",
    ) -> ProviderRunResult:
        # Paths must be valid inside the executor's environment (host cwd or the
        # container's /workspace); the result file is read back via the host mount.
        ws = executor.container_workspace()
        out_name = f"_provider_output_{session_name}.txt"
        output_file = f"{ws}/{out_name}"
        cmd = [
            "codex",
            "exec",
            "--json",
            "-m",
            provider_model,
            "-C",
            ws,
            "-s",
            "workspace-write",
            "--skip-git-repo-check",
            "--output-last-message",
            output_file,
            "-",
        ]

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

        input_tokens: Optional[int] = None
        cached_input_tokens: Optional[int] = None
        output_tokens: Optional[int] = None
        total_tokens: Optional[int] = None
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
                raw_input_tokens = usage.get("input_tokens")
                if raw_input_tokens is not None:
                    input_tokens = raw_input_tokens
                cached_input_tokens = usage.get("cached_input_tokens", cached_input_tokens)
                output_tokens = usage.get("output_tokens", output_tokens)
                # Normalize to canonical semantics where input excludes cached.
                if input_tokens is not None and cached_input_tokens is not None:
                    input_tokens = max(input_tokens - cached_input_tokens, 0)
                if input_tokens is not None and output_tokens is not None:
                    total_tokens = input_tokens + (cached_input_tokens or 0) + output_tokens
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
            provider_trace={
                "assistant_messages": assistant_messages,
                "tool_intents": tool_intents,
                "tool_results": tool_results,
            },
            raw_output=proc.stdout or "",
        )

    def build_provider_evidence(self, run_result: ProviderRunResult) -> str:
        trace = run_result.provider_trace or {}
        assistant_messages = trace.get("assistant_messages") or []
        tool_intents = trace.get("tool_intents") or []
        tool_results = trace.get("tool_results") or []

        lines: list[str] = []
        lines.append("PROVIDER_EVIDENCE")
        lines.append("provider: codex")
        lines.append("assistant_messages:")
        if assistant_messages:
            for msg in assistant_messages:
                lines.append(f"- {msg}")
        else:
            lines.append("- <none>")
        lines.append("tool_intents:")
        if tool_intents:
            for intent in tool_intents:
                lines.append(f"- {intent}")
        else:
            lines.append("- <none>")
        lines.append("tool_results:")
        if tool_results:
            for result in tool_results:
                lines.append(f"- {result}")
        else:
            lines.append("- <none>")
        return "\n".join(lines)

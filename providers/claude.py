from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Optional

from providers.base import Provider, ProviderRunResult

if TYPE_CHECKING:
    from runners.executor import Executor


def _compact_text(value: Any, limit: int = 200) -> str:
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


class ClaudeProvider(Provider):
    name = "claude"

    def run_task(
        self,
        prompt: str,
        workdir: str,
        provider_model: str,
        session_name: str,
        executor: "Executor",
    ) -> ProviderRunResult:
        # stream-json (+ --verbose, required with -p) emits the full event trace:
        # assistant messages with tool_use blocks, user tool_result blocks, and a
        # final `result` event with usage/cost. `json` would give only the final text.
        cmd = [
            "claude",
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            provider_model,
            "--dangerously-skip-permissions",
        ]

        # Authenticate as a real user via the login credentials (Keychain on macOS,
        # mounted ~/.claude/.credentials.json in containers) — NOT an API key. Blank
        # ANTHROPIC_API_KEY for this call so claude uses the subscription login instead
        # of falling back to key-based API billing.
        start = time.time()
        proc = executor.run(cmd, input_text=prompt, env_overrides={"ANTHROPIC_API_KEY": ""})
        elapsed_ms = int((time.time() - start) * 1000)

        result_text = ""
        input_tokens: Optional[int] = None
        cached_input_tokens: Optional[int] = None
        output_tokens: Optional[int] = None
        total_tokens: Optional[int] = None
        duration_ms: Optional[int] = None
        cost_usd: Optional[float] = None

        assistant_messages: list[str] = []
        tool_intents: list[str] = []
        tool_results: list[str] = []
        tool_names: dict[str, str] = {}  # tool_use_id -> tool name (to label results)

        for raw in (proc.stdout or "").splitlines():
            line = raw.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            typ = obj.get("type")

            if typ == "assistant":
                for block in (obj.get("message") or {}).get("content") or []:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "text":
                        text = (block.get("text") or "").strip()
                        if text:
                            assistant_messages.append(_compact_text(text, 360))
                    elif btype == "tool_use":
                        name = block.get("name") or "tool"
                        if block.get("id"):
                            tool_names[block["id"]] = name
                        tool_intents.append(f"{name}: {_compact_text(block.get('input'), 180)}")

            elif typ == "user":
                for block in (obj.get("message") or {}).get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        name = tool_names.get(block.get("tool_use_id"), "tool")
                        err = block.get("is_error")
                        tool_results.append(
                            f"tool={name}, success={not err}" if err is not None else f"tool={name}"
                        )

            elif typ == "result":
                result_text = str(obj.get("result", "")).strip()
                duration_ms = obj.get("duration_ms")
                cost_usd = obj.get("total_cost_usd")
                usage = obj.get("usage")
                if isinstance(usage, dict):
                    try:
                        # Canonical: input excludes cached (cache-read); cache_creation
                        # is fresh input written to cache.
                        fresh = int(usage.get("input_tokens") or 0)
                        cache_create = int(usage.get("cache_creation_input_tokens") or 0)
                        input_tokens = fresh + cache_create
                        raw_cache_read = usage.get("cache_read_input_tokens")
                        cached_input_tokens = (
                            int(raw_cache_read) if raw_cache_read is not None else None
                        )
                        raw_output = usage.get("output_tokens")
                        output_tokens = int(raw_output) if raw_output is not None else None
                        if output_tokens is not None:
                            total_tokens = input_tokens + (cached_input_tokens or 0) + output_tokens
                    except Exception:
                        pass

        if not result_text and assistant_messages:
            result_text = assistant_messages[-1]

        return ProviderRunResult(
            stdout=result_text,
            stderr=(proc.stderr or "").strip(),
            exit_code=proc.exit_code,
            elapsed_ms=elapsed_ms,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=None,
            total_tokens=total_tokens,
            provider_cost_usd=cost_usd,
            provider_trace={
                "assistant_messages": assistant_messages[-12:],
                "tool_intents": tool_intents[-24:],
                "tool_results": tool_results[-24:],
                "duration_ms": duration_ms,
                "cost_usd": cost_usd,
            },
            raw_output=proc.stdout or "",
        )

    def build_provider_evidence(self, run_result: ProviderRunResult) -> str:
        trace = run_result.provider_trace or {}
        assistant_messages = trace.get("assistant_messages") or []
        tool_intents = trace.get("tool_intents") or []
        tool_results = trace.get("tool_results") or []

        lines: list[str] = ["PROVIDER_EVIDENCE", "provider: claude", "assistant_messages:"]
        lines.extend([f"- {m}" for m in assistant_messages] or ["- <none>"])
        lines.append("tool_intents:")
        lines.extend([f"- {t}" for t in tool_intents] or ["- <none>"])
        lines.append("tool_results:")
        lines.extend([f"- {r}" for r in tool_results] or ["- <none>"])
        return "\n".join(lines)

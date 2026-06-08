from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING, Any, Optional

from providers.base import Provider, ProviderRunResult

if TYPE_CHECKING:
    from runners.executor import Executor

ANSI_ESCAPE_RE = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")


def _clean(text: str) -> str:
    text = ANSI_ESCAPE_RE.sub("", text)
    return "".join(ch for ch in text if ch in ("\n", "\t", "\r") or ord(ch) >= 32)


def _compact_text(value: Any, limit: int = 220) -> str:
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


def _iter_jsonl_records(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            # Ignore non-JSONL/noisy lines by design.
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def _extract_from_jsonl(
    records: list[dict[str, Any]],
) -> tuple[
    str,
    list[str],
    list[str],
    list[str],
    Optional[int],
    Optional[int],
    Optional[int],
    Optional[int],
    Optional[int],
]:
    assistant_messages: list[str] = []
    tool_intents: list[str] = []
    tool_results: list[str] = []

    input_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    last_cost_meta: Optional[dict[str, Any]] = None

    for obj in records:
        typ = str(obj.get("type", "")).strip().lower()
        if typ == "assistant":
            content = obj.get("content")
            msg = _compact_text(content, limit=360)
            if msg:
                assistant_messages.append(msg)
        elif typ == "tool_use":
            tool_name = obj.get("tool") or typ
            params = obj.get("params")
            if params is not None:
                tool_intents.append(f"{_compact_text(tool_name, 80)}: {_compact_text(params, 180)}")
            else:
                tool_intents.append(_compact_text(tool_name, 120))
        elif typ == "tool_result":
            tool_name = obj.get("tool") or "unknown"
            server = obj.get("server")
            success = obj.get("success")
            parts = [f"tool={_compact_text(tool_name, 80)}"]
            if server is not None:
                parts.append(f"server={_compact_text(server, 80)}")
            if success is not None:
                parts.append(f"success={success}")
            tool_results.append(", ".join(parts))
        elif typ == "cost":
            last_cost_meta = obj

    if last_cost_meta is not None:
        raw_in = last_cost_meta.get("input_tokens")
        raw_out = last_cost_meta.get("output_tokens")
        raw_cached = last_cost_meta.get("cache_read_tokens", last_cost_meta.get("cached_tokens"))
        raw_reasoning = last_cost_meta.get("reasoning_tokens")
        raw_total = last_cost_meta.get("session_tokens")
        try:
            if raw_in is not None:
                input_tokens = int(raw_in)
            if raw_out is not None:
                output_tokens = int(raw_out)
            if raw_cached is not None:
                cached_tokens = int(raw_cached)
            if raw_reasoning is not None:
                reasoning_tokens = int(raw_reasoning)
            if raw_total is not None:
                total_tokens = int(raw_total)
        except Exception:
            pass

    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens + (cached_tokens or 0) + (reasoning_tokens or 0)

    final_text = assistant_messages[-1] if assistant_messages else ""
    return (
        final_text,
        assistant_messages[-12:],
        tool_intents[-24:],
        tool_results[-24:],
        input_tokens,
        cached_tokens,
        output_tokens,
        reasoning_tokens,
        total_tokens,
    )


class OctomindProvider(Provider):
    name = "octomind"

    def run_task(
        self,
        prompt: str,
        workdir: str,
        provider_model: str,
        session_name: str,
        executor: "Executor",
    ) -> ProviderRunResult:
        # Run octomind's stock coding agent (`developer:general`) exactly as a real
        # user would. OCTOMIND_CONFIG_PATH (from the executor: host path or the
        # container's /cfg/octomind.toml) is the upstream baseline default.toml plus
        # a `judge` role; the baseline is untouched, so this is a fair, like-for-like
        # coding run vs `claude -p` / `codex exec`.
        main_cmd = [
            "octomind",
            "run",
            "developer:general",
            "--name",
            session_name,
            "--model",
            provider_model,
            "--format=jsonl",
        ]

        start = time.time()
        main = executor.run(
            main_cmd,
            env_overrides={"OCTOMIND_CONFIG_PATH": executor.octomind_config_path()},
            input_text=prompt,
        )
        elapsed_ms = int((time.time() - start) * 1000)

        combined = (main.stdout or "") + "\n" + (main.stderr or "")
        records = _iter_jsonl_records(combined)
        (
            final_text,
            assistant_messages,
            tool_intents,
            tool_results,
            input_tokens,
            cached_input_tokens,
            output_tokens,
            reasoning_tokens,
            total_tokens,
        ) = _extract_from_jsonl(records)

        if not final_text:
            # Fallback to legacy text extraction for non-jsonl output variants.
            final_text = _clean(main.stdout or "").strip()

        return ProviderRunResult(
            stdout=final_text,
            stderr=(main.stderr or "").strip(),
            exit_code=main.exit_code,
            elapsed_ms=elapsed_ms,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total_tokens,
            provider_trace={
                "assistant_messages": assistant_messages,
                "tool_intents": tool_intents,
                "tool_results": tool_results,
            },
        )

    def build_provider_evidence(self, run_result: ProviderRunResult) -> str:
        trace = run_result.provider_trace or {}
        assistant_messages = trace.get("assistant_messages") or []
        tool_intents = trace.get("tool_intents") or []
        tool_results = trace.get("tool_results") or []

        lines: list[str] = []
        lines.append("PROVIDER_EVIDENCE")
        lines.append("provider: octomind")
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

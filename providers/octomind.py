from __future__ import annotations

import json
import os
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
    assistant_messages: list[str] = []  # compacted, for judge-evidence trace
    full_assistant: list[str] = []       # full text, for the actual verdict
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
            # Preserve the FULL message (with newlines) for the verdict — QA/IFEval
            # grade this text. The compacted copy is only for the judge trace.
            full = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            full = (full or "").strip()
            if full:
                full_assistant.append(full)
                assistant_messages.append(_compact_text(content, limit=360))
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
        try:
            if raw_in is not None:
                input_tokens = int(raw_in)
            if raw_out is not None:
                output_tokens = int(raw_out)
            if raw_cached is not None:
                cached_tokens = int(raw_cached)
            if raw_reasoning is not None:
                reasoning_tokens = int(raw_reasoning)
        except Exception:
            pass

    # Always compute total from per-request fields, never from session_tokens
    # (which is cumulative across resumed sessions — summing it across turns
    # would double-count in multi-turn runs).
    if input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens + (reasoning_tokens or 0)

    final_text = full_assistant[-1] if full_assistant else ""
    return (
        final_text,
        assistant_messages[-12:],
        tool_intents,
        tool_results,
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
        resume_session_id: Optional[str] = None,
    ) -> ProviderRunResult:
        # Run octomind's stock coding agent (`developer:general`) exactly as a real
        # user would. OCTOMIND_CONFIG_PATH (from the executor: host path or the
        # container's /cfg/octomind.toml) is the upstream baseline default.toml plus
        # a `judge` role; the baseline is untouched, so this is a fair, like-for-like
        # coding run vs `claude -p` / `codex exec`.
        # Agent tag is task-appropriate: octobench picks octomind's coding agent
        # (developer:general) for coding cases and its general assistant
        # (assistant:general) for non-coding tasks (QA / instruction-following),
        # so we fairly test the framework's best-fit agent per task type.
        agent_tag = os.environ.get("OCTOMIND_AGENT", "developer:general")
        # OCTOMIND_WORKFLOW switches to octomind's multi-step workflow engine
        # (e.g. `develop`: context -> developer <-> evaluator loop). Workflows
        # take no --model flag; the model binds via a `[taps]` mapping appended
        # to the runtime config (see cli/swebench.py). Same stdin/jsonl contract.
        workflow = os.environ.get("OCTOMIND_WORKFLOW")
        if workflow:
            main_cmd = ["octomind", "workflow", workflow, "--format=jsonl"]
        else:
            main_cmd = [
                "octomind",
                "run",
                agent_tag,
                "--name",
                session_name,
                "--model",
                provider_model,
                "--format=jsonl",
            ]
            # Multi-turn: resume the named session. --name with an existing
            # session name auto-resumes in octomind, but -r is explicit.
            if resume_session_id:
                main_cmd.extend(["-r", resume_session_id])

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
            session_id=session_name,
            provider_trace={
                "assistant_messages": assistant_messages,
                "tool_intents": tool_intents,
                "tool_results": tool_results,
            },
            raw_output=main.stdout or "",
        )


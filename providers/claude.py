from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any, Optional

from providers.base import Provider, ProviderRunResult


def _compact_text(value: Any, limit: int = 360) -> str:
    if value is None:
        return ""
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
    ) -> ProviderRunResult:
        cmd = [
            "claude",
            "-p",
            "--output-format",
            "json",
            "--model",
            provider_model,
            "--dangerously-skip-permissions",
            "--bare",
            "--no-session-persistence",
        ]

        start = time.time()
        proc = subprocess.run(
            cmd,
            cwd=workdir,
            capture_output=True,
            text=True,
            input=prompt,
            env=os.environ.copy(),
        )
        elapsed_ms = int((time.time() - start) * 1000)

        result_text = ""
        input_tokens: Optional[int] = None
        cached_input_tokens: Optional[int] = None
        output_tokens: Optional[int] = None
        total_tokens: Optional[int] = None
        duration_ms: Optional[int] = None
        cost_usd: Optional[float] = None

        stdout_raw = (proc.stdout or "").strip()
        try:
            obj = json.loads(stdout_raw)
        except Exception:
            obj = None

        if isinstance(obj, dict):
            result_text = str(obj.get("result", "")).strip()
            duration_ms = obj.get("duration_ms")
            cost_usd = obj.get("total_cost_usd")

            usage = obj.get("usage")
            if isinstance(usage, dict):
                raw_input = usage.get("input_tokens")
                raw_cache_create = usage.get("cache_creation_input_tokens")
                raw_cache_read = usage.get("cache_read_input_tokens")
                raw_output = usage.get("output_tokens")

                try:
                    # Canonical: input_tokens excludes cached (cache-read).
                    # cache_creation tokens are fresh input written to cache.
                    fresh_input = int(raw_input) if raw_input is not None else 0
                    cache_create = int(raw_cache_create) if raw_cache_create is not None else 0
                    input_tokens = fresh_input + cache_create

                    cached_input_tokens = (
                        int(raw_cache_read) if raw_cache_read is not None else None
                    )
                    output_tokens = int(raw_output) if raw_output is not None else None

                    if input_tokens is not None and output_tokens is not None:
                        total_tokens = (
                            input_tokens + (cached_input_tokens or 0) + output_tokens
                        )
                except Exception:
                    pass
        else:
            result_text = stdout_raw

        return ProviderRunResult(
            stdout=result_text,
            stderr=(proc.stderr or "").strip(),
            exit_code=proc.returncode,
            elapsed_ms=elapsed_ms,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=None,
            total_tokens=total_tokens,
            provider_trace={
                "result": _compact_text(result_text),
                "duration_ms": duration_ms,
                "cost_usd": cost_usd,
            },
        )

    def build_provider_evidence(self, run_result: ProviderRunResult) -> str:
        trace = run_result.provider_trace or {}
        lines: list[str] = []
        lines.append("PROVIDER_EVIDENCE")
        lines.append("provider: claude")
        result = trace.get("result")
        if result:
            lines.append(f"result: {result}")
        else:
            lines.append("result: <none>")
        return "\n".join(lines)

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from providers.base import (
    Provider,
    ProviderRunResult,
    append_process_timing,
    shared_system_prompt,
)

if TYPE_CHECKING:
    from runners.executor import Executor

# Pi's JSON mode exits 0 after these; only the event stream reports them.
FAILED_STOP_REASONS = {"error", "aborted"}
FAILED_RESPONSE_EXIT_CODE = 1


@dataclass
class PiUsage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.cached_input_tokens
            + self.output_tokens
            + self.reasoning_tokens
        )

    def add(self, usage: dict[str, Any]) -> None:
        # Pi counts `reasoning` inside `output` and omits it when the model
        # API does not report it.
        reasoning = usage.get("reasoning", 0)
        self.input_tokens += usage["input"] + usage["cacheWrite"]
        self.cached_input_tokens += usage["cacheRead"]
        self.output_tokens += usage["output"] - reasoning
        self.reasoning_tokens += reasoning


@dataclass(frozen=True)
class PiOutput:
    final_text: str
    session_id: Optional[str]
    tool_names: list[str]
    usage: Optional[PiUsage]
    failure: Optional[str]


def parse_pi_output(stdout: str, resume_session_id: Optional[str]) -> PiOutput:
    final_text = ""
    session_id = resume_session_id
    tool_names: list[str] = []
    usage = PiUsage()
    responded = False
    failure: Optional[str] = "pi produced no assistant response"

    # Pi frames records on LF alone. str.splitlines() would also break on the
    # U+2028 and U+2029 that are legal inside its JSON strings.
    for line in stdout.split("\n"):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # Blank tail, or the last record of a killed process cut short.
            continue
        kind = event.get("type")
        if kind == "session" and session_id is None:
            session_id = event["id"]
        elif kind == "tool_execution_start":
            tool_names.append(event["toolName"])
        elif kind == "compaction_end" and "usage" in (event.get("result") or {}):
            usage.add(event["result"]["usage"])
        elif kind == "message_end" and event["message"]["role"] == "assistant":
            message = event["message"]
            responded = True
            usage.add(message["usage"])
            text = "".join(
                block["text"] for block in message["content"] if block["type"] == "text"
            ).strip()
            if text:
                final_text = text
            # Automatic retries can follow a failed attempt, so only the last
            # response decides the run.
            failure = (
                message.get("errorMessage") or message["stopReason"]
                if message["stopReason"] in FAILED_STOP_REASONS
                else None
            )

    return PiOutput(
        final_text=final_text,
        session_id=session_id,
        tool_names=tool_names,
        usage=usage if responded else None,
        failure=failure,
    )


class PiProvider(Provider):
    """pi (earendil-works/pi) via `pi --mode json`, prompt on stdin, model from
    configs/pi/models.json. Usage comes from the event stream, which covers
    exactly this process, so a resumed turn counts only its own requests."""

    name = "pi"

    def run_task(
        self,
        prompt: str,
        workdir: str,
        provider_model: str,
        session_name: str,
        executor: "Executor",
        resume_session_id: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
    ) -> ProviderRunResult:
        if reasoning_effort is not None:
            raise ValueError(
                "pi provider has no reasoning_effort wiring; "
                "pin it with a :<level> suffix on the model in configs/models.yaml"
            )
        cmd = [
            "pi",
            "--mode",
            "json",
            # Stops pi's version check and model catalog refresh, which a
            # sealed run cannot reach anyway.
            "--offline",
            # No benchmark extensions or skills exist; this keeps built-in and
            # repo-shipped ones out of the compared agent surface.
            "--no-extensions",
            "--no-skills",
            "--model",
            provider_model,
        ]
        system_prompt = shared_system_prompt()
        if system_prompt:
            cmd += ["--system-prompt", system_prompt]
        if resume_session_id:
            cmd += ["--session", resume_session_id]

        call_start_ms = time.time_ns() // 1_000_000
        started_at = time.monotonic()
        # Pi reads stdin to EOF before starting, so it must always be supplied.
        proc = executor.run(cmd, input_text=prompt)
        call_end_ms = time.time_ns() // 1_000_000
        elapsed_ms = int((time.monotonic() - started_at) * 1000)

        parsed = parse_pi_output(proc.stdout or "", resume_session_id)
        stderr = (proc.stderr or "").strip()
        exit_code = proc.exit_code
        if parsed.failure:
            stderr = "\n".join(part for part in (stderr, f"pi: {parsed.failure}") if part)
            exit_code = exit_code or FAILED_RESPONSE_EXIT_CODE
        usage = parsed.usage
        return ProviderRunResult(
            stdout=parsed.final_text,
            stderr=stderr,
            exit_code=exit_code,
            elapsed_ms=elapsed_ms,
            input_tokens=usage.input_tokens if usage else None,
            cached_input_tokens=usage.cached_input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
            reasoning_tokens=usage.reasoning_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            session_id=parsed.session_id,
            provider_trace={"tool_calls": parsed.tool_names},
            raw_output=append_process_timing(
                proc.stdout or "", call_start_ms, call_end_ms
            ),
        )

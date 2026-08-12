from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from runners.executor import Executor

# Same cap for every client: a longer trace must not buy a client more judge
# attention (favourable or otherwise) than a terser one.
PROVIDER_EVIDENCE_FINAL_MESSAGE_CHARS = 2000


def shared_system_prompt() -> Optional[str]:
    """The prompt every client must receive, or None when unset (stock behaviour).

    Octomind and opencode take it through their config files; the CLI-driven
    clients read it here so all four stay byte-identical to the one file.
    """
    path = os.environ.get("OCTOBENCH_SYSTEM_PROMPT")
    if not path:
        return None
    text = Path(path).read_text()
    if not text.strip():
        raise RuntimeError(f"OCTOBENCH_SYSTEM_PROMPT={path} is empty")
    return text


@dataclass
class ProviderRunResult:
    stdout: str
    stderr: str
    exit_code: int
    elapsed_ms: int
    input_tokens: Optional[int] = None
    cached_input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    # Provider-reported cost (authoritative when present). Claude reports
    # total_cost_usd itself, which correctly prices 1h cache WRITES at 2x input —
    # a component compute_cost() cannot see (cache_creation is folded into
    # input_tokens for the token columns).
    provider_cost_usd: Optional[float] = None
    provider_trace: Optional[dict[str, Any]] = None
    # Full raw agent output (the complete jsonl/event trace from the CLI) — saved
    # verbatim per run so the agent's every step/tool-call can be analyzed.
    raw_output: Optional[str] = None
    # Session ID for multi-turn resumption. Set by the provider on the first
    # turn; passed back as resume_session_id on subsequent turns so the agent
    # continues in the same conversation context.
    session_id: Optional[str] = None


class Provider(ABC):
    name: str

    @abstractmethod
    def run_task(
        self,
        prompt: str,
        workdir: str,
        provider_model: str,
        session_name: str,
        executor: "Executor",
        resume_session_id: Optional[str] = None,
    ) -> ProviderRunResult:
        raise NotImplementedError

    def build_provider_evidence(self, run_result: ProviderRunResult) -> str:
        """Client-agnostic trace block for judge context. Do NOT override.

        Scoring comes from the production diff and the validation exit code,
        both harness-produced. The only thing a trace adds is a completion
        claim the verdict can contradict, so that is all this carries.

        Anything client-specific here is scored as if it were work product:
        clients that exposed richer traces (tool params, tool results, every
        intermediate message) collected criticism that clients exposing less
        never received, and three of four announced themselves by name to the
        judge. Same work must yield the same payload, so the shape is fixed
        here and the provider name is deliberately absent.

        Kept to the final message alone because that is the one field also
        stored on the record (`result.stdout`), which lets rejudge rebuild
        this block byte-for-byte instead of re-parsing raw client traces.
        """
        final = (run_result.stdout or "").strip()
        if not final:
            return ""
        return "final_message:\n" + final[-PROVIDER_EVIDENCE_FINAL_MESSAGE_CHARS:]

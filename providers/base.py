from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from runners.executor import Executor


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
    provider_trace: Optional[dict[str, Any]] = None


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
    ) -> ProviderRunResult:
        raise NotImplementedError

    def build_provider_evidence(self, run_result: ProviderRunResult) -> str:
        """
        Provider-specific compact evidence for judge context.
        Override in provider implementations when richer trace is available.
        """
        return ""

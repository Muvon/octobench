from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Optional

from providers.base import Provider, ProviderRunResult

if TYPE_CHECKING:
    from runners.executor import Executor


class OpencodeProvider(Provider):
    """opencode (sst/opencode) via `opencode --pure run` with --auto permission
    approval and model via -m provider/model. No plugins are configured for the
    benchmark, so --pure preserves the agent surface while preventing opencode's
    unrelated first-run plugin install from entering the sealed/scored phase.
    The --format json event stream carries per-step token usage (summed across
    steps: each step is one API request) and the final assistant text."""

    name = "opencode"

    def run_task(
        self,
        prompt: str,
        workdir: str,
        provider_model: str,
        session_name: str,
        executor: "Executor",
        resume_session_id: Optional[str] = None,
    ) -> ProviderRunResult:
        cmd = [
            "opencode",
            "--pure",
            "run",
            "--auto",
            "--format",
            "json",
            "-m",
            provider_model,
        ]
        # Multi-turn sequences resume the SAME session, exactly like the other
        # clients: `opencode run -s <id>` continues a prior session. Without it
        # every turn starts from an empty context, which is not a cheaper agent
        # but a different benchmark — measured on rust/tokio, a memoryless
        # opencode held a flat ~15k prefix while resuming clients grew to 70k,
        # and it failed the one turn that depended on earlier work.
        if resume_session_id:
            cmd += ["--session", resume_session_id]
        cmd.append(prompt)

        # DockerExecutor uses `docker exec -i` because other providers receive
        # their prompt on stdin. OpenCode receives its prompt as argv; explicitly
        # close stdin or a tmux-backed campaign leaves the pipe open and
        # `opencode run` waits in its event loop before creating a session.
        start = time.time()
        proc = executor.run(cmd, input_text="")
        elapsed_ms = int((time.time() - start) * 1000)

        input_tokens = 0
        output_tokens = 0
        reasoning_tokens = 0
        cached_input = 0
        last_text: Optional[str] = None
        tool_titles: list[str] = []
        session_id: Optional[str] = resume_session_id

        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            part = obj.get("part") or {}
            typ = obj.get("type")
            if session_id is None:
                sid = part.get("sessionID") or obj.get("sessionID")
                if isinstance(sid, str) and sid:
                    session_id = sid
            if typ == "step_finish":
                tokens = part.get("tokens") or {}
                # Per-step counters, summed over the run: each step_finish is one
                # API request and reports only that request, so a resumed session
                # still bills only its own turn. Canonical
                # semantics, identical to the other clients: cache writes are
                # billed input, while reasoning remains separate from visible
                # output and is billed explicitly by compute_cost().
                cache = tokens.get("cache") or {}
                input_tokens += int(tokens.get("input") or 0) + int(cache.get("write") or 0)
                reasoning = int(tokens.get("reasoning") or 0)
                reasoning_tokens += reasoning
                output_tokens += int(tokens.get("output") or 0)
                cached_input += int(cache.get("read") or 0)
            elif typ == "text":
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    last_text = text
            elif typ == "tool_use":
                title = part.get("part", part).get("title") if isinstance(part, dict) else None
                tool = part.get("tool")
                if tool:
                    tool_titles.append(f"{tool}: {title or ''}".strip())

        total = input_tokens + cached_input + output_tokens + reasoning_tokens
        return ProviderRunResult(
            stdout=(last_text or "").strip(),
            stderr=(proc.stderr or "").strip(),
            exit_code=proc.exit_code,
            elapsed_ms=elapsed_ms,
            input_tokens=input_tokens or None,
            cached_input_tokens=cached_input or None,
            output_tokens=output_tokens or None,
            reasoning_tokens=reasoning_tokens or None,
            total_tokens=total or None,
            session_id=session_id,
            provider_trace={"tool_calls": tool_titles},
            raw_output=proc.stdout or "",
        )

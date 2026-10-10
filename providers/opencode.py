from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional

from providers.base import Provider, ProviderRunResult, append_process_timing

if TYPE_CHECKING:
    from runners.executor import Executor


@dataclass(frozen=True)
class OpencodeUsage:
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.cached_input_tokens
            + self.output_tokens
            + self.reasoning_tokens
        )


@dataclass(frozen=True)
class OpencodeOutput:
    final_text: str
    session_id: Optional[str]
    tool_titles: list[str]


@contextmanager
def open_opencode_db(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open the live OpenCode store read-only, including its WAL contents."""
    if not db_path.is_file():
        raise FileNotFoundError(f"OpenCode usage database not found: {db_path}")
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    try:
        yield db
    finally:
        db.close()


def read_opencode_usage(
    db_path: Path,
    root_session_id: str,
    start_ms: int,
    end_ms: int,
) -> OpencodeUsage:
    """Sum request usage for a root session tree inside an inclusive window."""
    if end_ms < start_ms:
        raise ValueError(f"OpenCode usage window ends before it starts: {start_ms}..{end_ms}")

    with open_opencode_db(db_path) as db:
        if db.execute("SELECT 1 FROM session WHERE id = ?", (root_session_id,)).fetchone() is None:
            raise ValueError(f"OpenCode session not found: {root_session_id}")
        rows = db.execute(
            """
            WITH RECURSIVE session_tree(id) AS (
                SELECT id FROM session WHERE id = ?
                UNION ALL
                SELECT session.id
                FROM session
                JOIN session_tree ON session.parent_id = session_tree.id
            )
            SELECT part.data
            FROM part
            JOIN session_tree ON part.session_id = session_tree.id
            WHERE part.time_created >= ?
              AND part.time_created <= ?
              AND json_extract(part.data, '$.type') = 'step-finish'
            ORDER BY part.time_created, part.id
            """,
            (root_session_id, start_ms, end_ms),
        ).fetchall()

    input_tokens = 0
    cached_input_tokens = 0
    output_tokens = 0
    reasoning_tokens = 0
    for (raw_data,) in rows:
        data = json.loads(raw_data)
        tokens = data["tokens"]
        cache = tokens["cache"]
        values = {
            "input": tokens["input"],
            "output": tokens["output"],
            "reasoning": tokens["reasoning"],
            "cache.read": cache["read"],
            "cache.write": cache["write"],
        }
        for name, value in values.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"OpenCode step-finish tokens.{name} is not an integer")
        input_tokens += values["input"] + values["cache.write"]
        cached_input_tokens += values["cache.read"]
        output_tokens += values["output"]
        reasoning_tokens += values["reasoning"]

    return OpencodeUsage(
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
    )


def parse_opencode_output(stdout: str, resume_session_id: Optional[str]) -> OpencodeOutput:
    last_text: Optional[str] = None
    tool_titles: list[str] = []
    session_id = resume_session_id

    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = obj.get("part") or {}
        typ = obj.get("type")
        if session_id is None:
            sid = part.get("sessionID") or obj.get("sessionID")
            if isinstance(sid, str) and sid:
                session_id = sid
        if typ == "text":
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                last_text = text
        elif typ == "tool_use":
            title = part.get("part", part).get("title") if isinstance(part, dict) else None
            tool = part.get("tool")
            if tool:
                tool_titles.append(f"{tool}: {title or ''}".strip())

    return OpencodeOutput(
        final_text=(last_text or "").strip(),
        session_id=session_id,
        tool_titles=tool_titles,
    )


class OpencodeProvider(Provider):
    """opencode (sst/opencode) via `opencode --pure run` with --auto permission
    approval and model via -m provider/model. No plugins are configured for the
    benchmark, so --pure preserves the agent surface while preventing opencode's
    unrelated first-run plugin install from entering the sealed/scored phase.
    The --format json event stream carries the final assistant text and trace;
    canonical request usage comes from OpenCode's session store so task-tool
    child sessions are included."""

    name = "opencode"

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
            raise ValueError("opencode provider has no reasoning_effort wiring")
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
        call_start_ms = time.time_ns() // 1_000_000
        started_at = time.monotonic()
        proc = executor.run(cmd, input_text="")
        call_end_ms = time.time_ns() // 1_000_000
        elapsed_ms = int((time.monotonic() - started_at) * 1000)

        parsed = parse_opencode_output(proc.stdout or "", resume_session_id)
        usage: Optional[OpencodeUsage] = None
        if parsed.session_id is not None:
            usage = read_opencode_usage(
                executor.opencode_state_host_path() / "opencode.db",
                parsed.session_id,
                call_start_ms,
                call_end_ms,
            )
        elif proc.exit_code == 0:
            raise RuntimeError("OpenCode run did not report a session id")
        # A run that failed before opening a session has no usage to read; the
        # caller records it as a provider failure with unknown cost.
        return ProviderRunResult(
            stdout=parsed.final_text,
            stderr=(proc.stderr or "").strip(),
            exit_code=proc.exit_code,
            elapsed_ms=elapsed_ms,
            input_tokens=usage.input_tokens if usage else None,
            cached_input_tokens=usage.cached_input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
            reasoning_tokens=usage.reasoning_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            session_id=parsed.session_id,
            provider_trace={"tool_calls": parsed.tool_titles},
            raw_output=append_process_timing(
                proc.stdout or "", call_start_ms, call_end_ms
            ),
        )

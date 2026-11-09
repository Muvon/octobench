from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from providers.pi import FAILED_RESPONSE_EXIT_CODE, PiProvider, parse_pi_output

MODEL = "isoquant/deepseek-v4.1-flash-1017-fast:low"


def usage(
    fresh: int = 0,
    output: int = 0,
    cache_read: int = 0,
    cache_write: int = 0,
    reasoning: int | None = None,
) -> dict[str, int]:
    fields = {
        "input": fresh,
        "output": output,
        "cacheRead": cache_read,
        "cacheWrite": cache_write,
        "totalTokens": fresh + output + cache_read + cache_write,
    }
    return fields if reasoning is None else {**fields, "reasoning": reasoning}


def assistant(
    text: str = "",
    stop_reason: str = "stop",
    tokens: dict[str, int] | None = None,
    error: str | None = None,
) -> dict[str, object]:
    message: dict[str, object] = {
        "role": "assistant",
        "content": [{"type": "text", "text": text}] if text else [],
        "usage": tokens or usage(),
        "stopReason": stop_reason,
    }
    if error:
        message["errorMessage"] = error
    return {"type": "message_end", "message": message}


def stream(*events: dict[str, object]) -> str:
    return "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events)


class FakeExecutor:
    def __init__(self, stdout: str, exit_code: int = 0, stderr: str = "") -> None:
        self.result = SimpleNamespace(stdout=stdout, stderr=stderr, exit_code=exit_code)
        self.argv: list[str] = []
        self.input_text: str | None = None

    def run(self, argv: list[str], input_text: str | None = None) -> SimpleNamespace:
        self.argv = argv
        self.input_text = input_text
        return self.result


def run_task(executor: FakeExecutor, resume_session_id: str | None = None):
    return PiProvider().run_task(
        prompt="fix it",
        workdir="/workspace",
        provider_model=MODEL,
        session_name="s",
        executor=executor,
        resume_session_id=resume_session_id,
    )


class ParsePiOutputTest(unittest.TestCase):
    def test_sums_responses_and_compaction_and_separates_reasoning(self) -> None:
        parsed = parse_pi_output(
            stream(
                {"type": "session", "id": "sid", "version": 3},
                assistant(tokens=usage(10, 30, 100, 5, reasoning=20)),
                {"type": "tool_execution_start", "toolName": "bash"},
                {"type": "compaction_end", "result": {"usage": usage(7, 3)}},
                {"type": "compaction_end", "aborted": True},
                assistant("first"),
                assistant("done", tokens=usage(1, 2)),
            ),
            None,
        )

        assert parsed.usage is not None
        self.assertEqual(parsed.usage.input_tokens, 23)
        self.assertEqual(parsed.usage.cached_input_tokens, 100)
        self.assertEqual(parsed.usage.output_tokens, 15)
        self.assertEqual(parsed.usage.reasoning_tokens, 20)
        self.assertEqual(parsed.usage.total_tokens, 158)
        self.assertEqual(parsed.final_text, "done")
        self.assertEqual(parsed.session_id, "sid")
        self.assertEqual(parsed.tool_names, ["bash"])
        self.assertIsNone(parsed.failure)

    def test_line_separator_inside_a_string_keeps_the_record_whole(self) -> None:
        parsed = parse_pi_output(stream(assistant("one two")), None)

        self.assertEqual(parsed.final_text, "one two")

    def test_truncated_last_record_is_ignored(self) -> None:
        parsed = parse_pi_output(stream(assistant("kept")) + '{"type":"message_e', None)

        self.assertEqual(parsed.final_text, "kept")

    def test_retried_failure_does_not_fail_the_run(self) -> None:
        parsed = parse_pi_output(
            stream(assistant(stop_reason="error", error="529"), assistant("done")), None
        )

        self.assertIsNone(parsed.failure)

    def test_resume_keeps_the_session_id(self) -> None:
        parsed = parse_pi_output(stream(assistant("done")), "sid")

        self.assertEqual(parsed.session_id, "sid")


class PiRunTaskTest(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("OCTOBENCH_SYSTEM_PROMPT", None)

    def test_prompt_goes_on_stdin_and_resume_uses_the_session(self) -> None:
        executor = FakeExecutor(stream(assistant("done")))

        result = run_task(executor, "sid")

        self.assertEqual(executor.input_text, "fix it")
        self.assertEqual(executor.argv[:3], ["pi", "--mode", "json"])
        self.assertEqual(executor.argv[-4:], ["--model", MODEL, "--session", "sid"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout, "done")

    def test_shared_system_prompt_replaces_pi_default(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            prompt_path = Path(raw_tmp) / "prompt.md"
            prompt_path.write_text("shared rules")
            os.environ["OCTOBENCH_SYSTEM_PROMPT"] = str(prompt_path)
            executor = FakeExecutor(stream(assistant("done")))

            run_task(executor)

        index = executor.argv.index("--system-prompt")
        self.assertEqual(executor.argv[index + 1], "shared rules")

    def test_failed_final_response_becomes_a_failed_run(self) -> None:
        executor = FakeExecutor(stream(assistant(stop_reason="error", error="529 overloaded")))

        result = run_task(executor)

        self.assertEqual(result.exit_code, FAILED_RESPONSE_EXIT_CODE)
        self.assertIn("529 overloaded", result.stderr)
        self.assertEqual(result.total_tokens, 0)

    def test_no_response_fails_with_unknown_usage(self) -> None:
        result = run_task(FakeExecutor(""))

        self.assertEqual(result.exit_code, FAILED_RESPONSE_EXIT_CODE)
        self.assertIsNone(result.total_tokens)

    def test_process_failure_keeps_exit_code_and_timeout_marker(self) -> None:
        marker = "octobench: case timeout after 10s"

        result = run_task(FakeExecutor("", exit_code=124, stderr=marker))

        self.assertEqual(result.exit_code, 124)
        self.assertIn(marker, result.stderr)

    def test_reasoning_effort_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PiProvider().run_task(
                prompt="fix it",
                workdir="/workspace",
                provider_model=MODEL,
                session_name="s",
                executor=FakeExecutor(""),
                reasoning_effort="low",
            )


if __name__ == "__main__":
    unittest.main()

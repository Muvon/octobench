#!/usr/bin/env python3
"""Offline self-test for the benchmark framework.

Validates the registry + every config + the objective matchers + constraint engine
+ scoring, WITHOUT touching the network or any model API. Run before trusting a
live bench run:

    python3 scripts/bench_selftest.py
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from benchmarks import verify  # noqa: E402
from benchmarks.base import RunContext, finalize_scoring  # noqa: E402
from benchmarks.registry import build_adapter, list_benchmarks  # noqa: E402
from cli.main import GUARDRAILS_TOML  # noqa: E402
from scoring.aggregate import (  # noqa: E402
    TOKEN_SEMANTICS,
    compute_cost,
    normalize_token_counts,
)
from providers.opencode import OpencodeProvider  # noqa: E402

_passed = 0
_failed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {name} {detail}")


def test_configs() -> None:
    rows = list_benchmarks(REPO)
    print(f"[configs] {len(rows)} benchmark config(s)")
    check("at least 8 configs", len(rows) >= 8, f"got {len(rows)}")
    for name, _cfg in rows:
        try:
            a = build_adapter(REPO, name)
            check(f"build {name}", a is not None)
        except Exception as e:  # noqa: BLE001
            check(f"build {name}", False, str(e))


def test_mcq() -> None:
    choices = ["Paris", "London", "Rome", "Berlin"]
    check("mcq letter gold", verify.mcq_match("B", "B", choices))
    check("mcq index gold (0-based)", verify.mcq_match("A", 0, choices))
    check("mcq text gold", verify.mcq_match("Rome", "Rome", choices))
    check("mcq 'answer is (C)'", verify.mcq_match("the answer is (C)", "C", choices))
    check("mcq wrong", not verify.mcq_match("A", "B", choices))


def test_final_answer() -> None:
    check("numeric exact", verify.final_answer_match("70", 70, "numeric"))
    check("numeric in text", verify.final_answer_match("ANSWER: 70", "70", "numeric"))
    check("numeric tol", verify.final_answer_match("3.14159", 3.1415926, "numeric", tol=1e-3))
    check("math boxed", verify.final_answer_match(r"so \boxed{42}", "42", "math"))
    check("string norm", verify.final_answer_match("Hello, World.", "hello world", "string"))
    check("numeric wrong", not verify.final_answer_match("69", 70, "numeric"))
    # letter mode (HLE multipleChoice): bare letter and "letter. text" both match
    check("letter bare", verify.final_answer_match("D", "D", "letter"))
    check("letter with text", verify.final_answer_match("D. Weak Non-Sadism", "D", "letter"))
    check("letter paren", verify.final_answer_match("(C)", "C", "letter"))
    check("letter wrong", not verify.final_answer_match("A. Something", "D", "letter"))


def test_constraints() -> None:
    # IFEval-style spec: no comma + at least 5 words.
    spec = {
        "instruction_id_list": ["punctuation:no_comma", "length_constraints:number_words"],
        "kwargs": [{}, {"relation": "at least", "num_words": 5}],
    }
    ok, d = verify.verify_constraints("this reply has no commas at all", spec)
    check("constraints pass", ok is True, str(d))
    bad, _ = verify.verify_constraints("too short, oops", spec)
    check("constraints fail (comma+short)", bad is False)
    none_obj, _ = verify.verify_constraints(
        "x", {"instruction_id_list": ["totally:unknown"], "kwargs": [{}]}
    )
    check("unknown constraint -> None", none_obj is None)
    # inline short-form
    inline = [{"type": "lowercase"}, {"type": "word_count", "relation": "at most", "num_words": 3}]
    ok2, _ = verify.verify_constraints("all lower", inline)
    check("inline lowercase+short pass", ok2 is True)


def test_ifbench() -> None:
    """Vendored IFBench checkers (needs nltk/emoji/syllapy; first run may download
    nltk corpora into benchmarks/ifbench_vendor/.nltk_data)."""
    spec = {
        "instruction_id_list": ["count:word_count_range"],
        "kwargs": [{"min_words": 3, "max_words": 5}],
    }
    ok, d = verify.verify_constraints("one two three four", spec)
    check("ifbench word_count_range pass", ok is True, str(d))
    bad, _ = verify.verify_constraints("one two", spec)
    check("ifbench word_count_range fail", bad is False)
    mixed = {
        "instruction_id_list": ["punctuation:no_comma", "count:unique_word_count"],
        "kwargs": [{}, {"N": 3}],
    }
    ok2, d2 = verify.verify_constraints("red green blue red", mixed)
    check("ifeval+ifbench mixed pass", ok2 is True, str(d2))


def test_scoring() -> None:
    ctx = RunContext(
        repo_root=REPO,
        models_cfg={},
        judge_cfg={},
        scoring_cfg={
            "judge_weight": 0.85,
            "efficiency_weight": 0.15,
            "validation_fail_penalty": 25.0,
        },
        efficiency_cfg={"latency_ms": 8000, "cost_usd": 0.2, "tps": 50},
        out_dir=REPO,
    )

    def rec(objective):
        return {
            "result": {"elapsed_ms": 4000},
            "tokens": {"total": 1200},
            "cost_usd": 0.05,
            "scripts": {"validate": {"exit_code": 0 if objective else 1}},
            "verdict": {"objective": objective},
            "judge": {"score": 80},
        }

    r1 = rec(True)
    finalize_scoring(r1, ctx)
    check("objective True -> final 100", r1["scoring"]["final_score"] == 100.0, str(r1["scoring"]))
    r0 = rec(False)
    finalize_scoring(r0, ctx)
    check("objective False -> final 0", r0["scoring"]["final_score"] == 0.0)
    rn = rec(None)
    rn["scripts"]["validate"]["exit_code"] = 0
    finalize_scoring(rn, ctx)
    check("judge_text -> weighted final >0", rn["scoring"]["final_score"] > 0)


def test_token_accounting() -> None:
    pricing = {"input": 0.14, "cached_input": 0.0028, "output": 0.28}
    expected = (100 * 0.14 + 200 * 0.0028 + (300 + 400) * 0.28) / 1_000_000
    actual = compute_cost(100, 200, 300, pricing, 400)
    check("reasoning billed once", actual is not None and abs(actual - expected) < 1e-12)

    old_separate = {
        "input": 100,
        "cached_input": 200,
        "output": 300,
        "reasoning": 400,
        "total": 800,
    }
    check(
        "legacy separate reasoning preserved",
        normalize_token_counts(old_separate) == (100, 200, 300, 400),
    )

    old_folded = {
        "input": 100,
        "cached_input": 200,
        "output": 700,
        "reasoning": 400,
        "total": 1000,
    }
    check(
        "legacy folded reasoning normalized",
        normalize_token_counts(old_folded) == (100, 200, 300, 400),
    )

    ambiguous = {**old_folded, "cached_input": 400, "total": 1200}
    try:
        normalize_token_counts(ambiguous)
    except ValueError:
        ambiguous_rejected = True
    else:
        ambiguous_rejected = False
    check("ambiguous legacy semantics rejected", ambiguous_rejected)

    current = {**old_separate, "semantics": TOKEN_SEMANTICS, "total": 1000}
    check(
        "current token semantics preserved",
        normalize_token_counts(current) == (100, 200, 300, 400),
    )


def test_provider_commands() -> None:
    class Result:
        stdout = ""
        stderr = ""
        exit_code = 0

    class Executor:
        argv = []
        input_text = None

        @staticmethod
        def container_workspace() -> str:
            return "/workspace"

        @staticmethod
        def workspace_host_path() -> Path:
            return Path("/__octobench_selftest_missing__")

        def run(self, argv, input_text=None):
            self.argv = argv
            self.input_text = input_text
            return Result()

    executor = Executor()
    OpencodeProvider().run_task(
        prompt="test",
        workdir="/workspace",
        provider_model="alibaba/glm-5.2",
        session_name="selftest",
        executor=executor,
    )
    check(
        "opencode skips unconfigured plugin bootstrap",
        executor.argv[:3] == ["opencode", "--pure", "run"],
        str(executor.argv),
    )
    check(
        "opencode closes inherited stdin",
        executor.input_text == "",
        repr(executor.input_text),
    )


def test_guardrails() -> None:
    try:
        parsed = tomllib.loads(GUARDRAILS_TOML)
    except tomllib.TOMLDecodeError as exc:
        check("offline guardrails parse as TOML", False, str(exc))
        return
    check(
        "offline guardrails deny websearch",
        parsed.get("guard") == [
            {
                "match": "websearch",
                "message": parsed["guard"][0]["message"],
            }
        ]
        and "Web search is DISABLED" in parsed["guard"][0]["message"],
        str(parsed),
    )


def main() -> None:
    print("octobench benchmark framework self-test\n")
    test_configs()
    test_mcq()
    test_final_answer()
    test_constraints()
    test_ifbench()
    test_scoring()
    test_token_accounting()
    test_provider_commands()
    test_guardrails()
    print(f"\n{_passed} passed, {_failed} failed")
    sys.exit(1 if _failed else 0)


if __name__ == "__main__":
    main()

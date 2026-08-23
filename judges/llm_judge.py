from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from judges.prompts import JUDGE_SYSTEM, JUDGE_TEMPLATE
from runners.cli_runner import run_cli

ANSI_ESCAPE_RE = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")


def _strip_terminal_noise(text: str) -> str:
    # Remove ANSI escape sequences and non-printing control chars except newlines/tabs.
    text = ANSI_ESCAPE_RE.sub("", text)
    return "".join(ch for ch in text if ch in ("\n", "\t", "\r") or ord(ch) >= 32)


def _escape_control_chars_in_json_strings(s: str) -> str:
    """
    Make near-JSON parseable by escaping raw control chars inside quoted strings.
    This handles LLM outputs that inject literal newlines inside JSON string values.
    """
    out = []
    in_str = False
    escaped = False
    for ch in s:
        if in_str:
            if escaped:
                out.append(ch)
                escaped = False
                continue
            if ch == "\\":
                out.append(ch)
                escaped = True
                continue
            if ch == '"':
                out.append(ch)
                in_str = False
                continue
            if ch == "\n":
                out.append("\\n")
                continue
            if ch == "\r":
                out.append("\\r")
                continue
            if ch == "\t":
                out.append("\\t")
                continue
            if ord(ch) < 32:
                out.append(f"\\u{ord(ch):04x}")
                continue
            out.append(ch)
        else:
            out.append(ch)
            if ch == '"':
                in_str = True
                escaped = False
    return "".join(out)


def _extract_json(text: str) -> Dict:
    text = _strip_terminal_noise(text)

    # Preferred: explicit tagged payload. Greedy {.*} (not {.*?}) so a `}` inside a
    # string value (judge reasoning often quotes code) doesn't truncate the JSON —
    # the closing </results> tag bounds the match.
    tagged = re.search(r"<results>\s*(\{.*\})\s*</results>", text, re.DOTALL)
    if tagged:
        payload = tagged.group(1)
        try:
            return json.loads(payload)
        except Exception:
            return json.loads(_escape_control_chars_in_json_strings(payload))

    # Fallback: parse first valid JSON object from any text
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
            if isinstance(obj, dict):
                return obj
        except Exception:
            # Try repaired JSON from this position.
            repaired = _escape_control_chars_in_json_strings(text[i:])
            try:
                obj, _ = decoder.raw_decode(repaired)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue

    raise ValueError("No JSON found in judge output")


def _cfg_for_model(judge_cfg: Dict, model: str) -> Dict:
    cfg = dict(judge_cfg)
    cfg["model"] = model
    command = list(cfg.get("command", []))
    if "-m" in command:
        command[command.index("-m") + 1] = model
    cfg["command"] = command
    return cfg


def _run_single_judge(prompt: str, judge_cfg: Dict, workdir: str) -> Dict:
    result = run_cli(prompt, workdir, judge_cfg)
    raw = result.stdout.strip() if result.stdout.strip() else result.stderr.strip()
    try:
        data = _extract_json(raw)
    except Exception as e:
        # Fallback: return a structured error so runs still complete
        data = {
            "score": 0,
            "reasoning": "Judge output not valid JSON",
            "issues": [f"Judge parse error: {str(e)}"],
            "confidence": 0.0,
        }
        data["_judge_parse_error"] = True

    data["_judge_raw"] = raw
    data["_judge_exit_code"] = result.exit_code
    data["_judge_elapsed_ms"] = result.elapsed_ms
    return data


# Judge payload budget. The panel runs on models with a hard context ceiling, and
# nothing bounded these logs: a case with a wide diff or a chatty test suite built
# a 212K-token prompt, every panel model returned "context remains above the usable
# ceiling", and the case scored 0 with a passing validation exit code — a scoring
# failure that reads exactly like a bad answer. Clamp per field, keeping the head
# (what was attempted) and the tail (where suites report failures).
JUDGE_BUDGET = {
    # field: (head_chars, tail_chars)
    "prep_log": (0, 8_000),
    "quality_log": (0, 8_000),
    "validation_log": (4_000, 24_000),
    "evidence_log": (60_000, 20_000),
}


# A score is the mean of the FULL panel or it is not a score. Averaging only the
# judges that happened to answer silently changes the rubric per record: a turn
# judged by one model is not comparable to one judged by three, and the case that
# scored 0 next to a passing exit code looked exactly like a bad answer. Missing
# judges are retried; a panel still short after this many rounds is recorded as
# unjudged for scripts/audit_judges.py to find, never as a low score.
JUDGE_PANEL_ATTEMPTS = 3
JUDGE_RETRY_BACKOFF_S = 10


def _is_valid_verdict(v: Dict) -> bool:
    """A verdict that may enter the panel mean.

    Empty-zero verdicts (score 0 with no reasoning) are failed judgments that
    happened to parse — a genuine 0 has to say why.
    """
    if v.get("_judge_parse_error") or not isinstance(v.get("score"), (int, float)):
        return False
    return not (float(v["score"]) == 0 and not str(v.get("reasoning") or "").strip())


def _clamp(text: str, head: int, tail: int) -> str:
    if not text or len(text) <= head + tail:
        return text
    dropped = len(text) - head - tail
    marker = f"\n\n[... {dropped} characters elided by the judge payload budget ...]\n\n"
    return text[:head] + marker + (text[-tail:] if tail else "")


def run_judge(prompt_payload: Dict, judge_cfg: Dict, workdir: str) -> Dict:
    task = prompt_payload["task"]
    prep_log = _clamp(prompt_payload.get("prep_log", ""), *JUDGE_BUDGET["prep_log"])
    quality_log = _clamp(prompt_payload.get("quality_log", ""), *JUDGE_BUDGET["quality_log"])
    validation_log = _clamp(prompt_payload.get("validation_log", ""), *JUDGE_BUDGET["validation_log"])
    evidence_log = _clamp(prompt_payload.get("evidence_log", ""), *JUDGE_BUDGET["evidence_log"])

    # The verdict comes from the test command's exit code. Without it the judge
    # has to infer pass/fail from log prose, which misreads every suite that
    # prints expected failures (Catch2 [!shouldfail], pytest xfail, ...).
    exit_code = prompt_payload.get("validation_exit_code")
    if exit_code is None:
        validation_verdict = "UNKNOWN (exit code not supplied)"
    else:
        validation_verdict = (
            f"{'PASS' if exit_code == 0 else 'FAIL'} "
            f"(test command exit code {exit_code})"
        )

    prompt = f"System:\n{JUDGE_SYSTEM}\n\n" + JUDGE_TEMPLATE.format(
        task=task,
        prep_log=prep_log,
        quality_log=quality_log,
        validation_verdict=validation_verdict,
        validation_log=validation_log,
        evidence_log=evidence_log,
    )

    models = judge_cfg.get("models") or [judge_cfg.get("model")]
    if len(models) == 1:
        data = _run_single_judge(prompt, _cfg_for_model(judge_cfg, models[0]), workdir)
        data["_judge_model"] = models[0]
        return data

    # Panel: every model judges the SAME payload independently (in parallel —
    # wall time stays that of the slowest judge); the record's score/confidence
    # are the mean over the whole panel, retried until every judge answers.
    def _judge_one(model: str) -> Dict:
        v = _run_single_judge(prompt, _cfg_for_model(judge_cfg, model), workdir)
        v["_judge_model"] = model
        return v

    by_model: Dict[str, Dict] = {}
    pending = list(models)
    for attempt in range(JUDGE_PANEL_ATTEMPTS):
        if attempt:
            print(f"[judge] panel short — retry {attempt}/{JUDGE_PANEL_ATTEMPTS - 1}"
                  f" for {pending}", file=sys.stderr, flush=True)
            time.sleep(JUDGE_RETRY_BACKOFF_S * attempt)
        with ThreadPoolExecutor(max_workers=len(pending)) as pool:
            for v in pool.map(_judge_one, pending):
                by_model[v["_judge_model"]] = v
        pending = [m for m in models if not _is_valid_verdict(by_model[m])]
        if not pending:
            break

    verdicts = [by_model[m] for m in models]
    valid = [v for v in verdicts if _is_valid_verdict(v)]
    if pending:
        print(f"[judge] INCOMPLETE PANEL — {len(valid)}/{len(models)} verdicts after "
              f"{JUDGE_PANEL_ATTEMPTS} attempts; missing {pending}",
              file=sys.stderr, flush=True)
        data = {
            "score": 0,
            "reasoning": f"Incomplete panel: {len(valid)}/{len(models)} judges "
                         f"produced a verdict after {JUDGE_PANEL_ATTEMPTS} attempts",
            "issues": [f"{m}: no verdict" for m in pending],
            "confidence": 0.0,
            "_judge_parse_error": True,
            "_judge_incomplete": True,
        }
    else:
        data = {
            "score": round(sum(float(v["score"]) for v in valid) / len(valid), 2),
            "confidence": round(
                sum(float(v.get("confidence") or 0) for v in valid) / len(valid), 3
            ),
            "reasoning": " | ".join(
                f"{v['_judge_model']}={v['score']}: "
                + str(v.get("reasoning", "")).split("\n")[0][:200]
                for v in valid
            ),
            "issues": [i for v in valid for i in (v.get("issues") or [])],
        }
    data["judges"] = [
        {
            "model": v["_judge_model"],
            "score": v.get("score"),
            "confidence": v.get("confidence"),
            "reasoning": v.get("reasoning"),
            "issues": v.get("issues"),
            "parse_error": bool(v.get("_judge_parse_error")),
            "elapsed_ms": v.get("_judge_elapsed_ms"),
        }
        for v in verdicts
    ]
    data["_judge_raw"] = "\n\n===== JUDGE SEPARATOR =====\n\n".join(
        f"[{v['_judge_model']}]\n{v.get('_judge_raw', '')}" for v in verdicts
    )
    data["_judge_exit_code"] = max(v.get("_judge_exit_code") or 0 for v in verdicts)
    data["_judge_elapsed_ms"] = sum(v.get("_judge_elapsed_ms") or 0 for v in verdicts)
    return data


if __name__ == "__main__":
    # parser self-check: a `}` inside a string value must not truncate the payload
    out = _extract_json('log noise <results>{"score": 7, "reasoning": "used dict {k: v}"}</results> tail')
    assert out["score"] == 7 and out["reasoning"].endswith("}"), out

    # panel self-check: a judge that fails once is retried and its verdict counts;
    # a judge that never answers leaves the record unjudged, not low-scored.
    assert _is_valid_verdict({"score": 90, "reasoning": "ok"})
    assert not _is_valid_verdict({"score": 0, "reasoning": ""})
    assert not _is_valid_verdict({"score": 90, "_judge_parse_error": True})

    JUDGE_RETRY_BACKOFF_S = 0
    calls: Dict[str, int] = {}

    def _fake(prompt, cfg, workdir, _flaky=("b",), _dead=("c",)):
        m = cfg["model"]
        calls[m] = calls.get(m, 0) + 1
        if m in _dead or (m in _flaky and calls[m] == 1):
            return {"score": 0, "reasoning": "", "_judge_parse_error": True}
        return {"score": 90, "reasoning": "fine", "confidence": 0.9}

    _real, _run_single_judge = _run_single_judge, _fake
    cfg = {"models": ["a", "b", "c"], "command": []}
    payload = {"task": "t", "validation_exit_code": 0}
    assert run_judge(payload, {**cfg, "models": ["a", "b"]}, ".")["score"] == 90
    assert calls["b"] == 2, calls          # the flaky judge was retried, not dropped
    incomplete = run_judge(payload, cfg, ".")
    assert incomplete["_judge_incomplete"] and incomplete["confidence"] == 0.0
    assert calls["c"] == JUDGE_PANEL_ATTEMPTS, calls
    _run_single_judge = _real
    print("ok")

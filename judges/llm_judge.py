from __future__ import annotations

import json
import re
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


def run_judge(prompt_payload: Dict, judge_cfg: Dict, workdir: str) -> Dict:
    task = prompt_payload["task"]
    prep_log = prompt_payload.get("prep_log", "")
    quality_log = prompt_payload.get("quality_log", "")
    validation_log = prompt_payload.get("validation_log", "")
    evidence_log = prompt_payload.get("evidence_log", "")

    prompt = f"System:\n{JUDGE_SYSTEM}\n\n" + JUDGE_TEMPLATE.format(
        task=task,
        prep_log=prep_log,
        quality_log=quality_log,
        validation_log=validation_log,
        evidence_log=evidence_log,
    )

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


if __name__ == "__main__":
    # parser self-check: a `}` inside a string value must not truncate the payload
    out = _extract_json('log noise <results>{"score": 7, "reasoning": "used dict {k: v}"}</results> tail')
    assert out["score"] == 7 and out["reasoning"].endswith("}"), out
    print("ok")

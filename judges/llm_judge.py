from __future__ import annotations

import json
import re
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

    models = judge_cfg.get("models") or [judge_cfg.get("model")]
    if len(models) == 1:
        data = _run_single_judge(prompt, _cfg_for_model(judge_cfg, models[0]), workdir)
        data["_judge_model"] = models[0]
        return data

    # Panel: every model judges the SAME payload independently (in parallel —
    # wall time stays that of the slowest judge); the record's score/confidence
    # are the mean over judges that produced a valid verdict.
    def _judge_one(model: str) -> Dict:
        v = _run_single_judge(prompt, _cfg_for_model(judge_cfg, model), workdir)
        v["_judge_model"] = model
        return v

    with ThreadPoolExecutor(max_workers=len(models)) as pool:
        verdicts = list(pool.map(_judge_one, models))

    valid = [
        v for v in verdicts
        if not v.get("_judge_parse_error")
        and isinstance(v.get("score"), (int, float))
        # Empty-zero verdicts (score 0, no reasoning) are failed judgments that
        # happened to parse — a genuine 0 must say why. Exclude from the mean.
        and not (float(v["score"]) == 0 and not str(v.get("reasoning") or "").strip())
    ]
    if not valid:
        data = {
            "score": 0,
            "reasoning": "All panel judges failed to produce a verdict",
            "issues": [f"{v['_judge_model']}: {v.get('issues')}" for v in verdicts],
            "confidence": 0.0,
            "_judge_parse_error": True,
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
    print("ok")

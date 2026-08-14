from __future__ import annotations

from typing import Dict, Optional


TOKEN_SEMANTICS = "separate_reasoning_v1"


def normalize_token_counts(tokens: Dict) -> tuple[int, int, int, int]:
    """Return fresh input, cache reads, visible output, and reasoning.

    Unmarked records from a short-lived schema folded reasoning into output.
    Their stored total is input + cache + folded output, which distinguishes
    them from the older and current separate-reasoning representations.
    """
    fresh = int(tokens.get("input") or 0)
    cache = int(tokens.get("cached_input") or 0)
    output = int(tokens.get("output") or 0)
    reasoning = int(tokens.get("reasoning") or 0)
    total = int(tokens.get("total") or 0)
    semantics = tokens.get("semantics")
    folded = semantics == "reasoning_in_output_v0"
    if not semantics and reasoning > 0:
        matches_separate = total in {
            fresh + output,
            fresh + output + reasoning,
        }
        matches_folded = total == fresh + cache + output
        if matches_separate and matches_folded:
            raise ValueError(
                "ambiguous unmarked token semantics; set tokens.semantics explicitly"
            )
        folded = matches_folded
    if folded:
        output = max(output - reasoning, 0)
    return fresh, cache, output, reasoning


def _exp_score(value: float, scale: float, invert: bool = False) -> float:
    import math

    if scale <= 0:
        return 0.0
    if invert:
        return 100.0 * (1.0 - math.exp(-value / scale))
    return 100.0 * math.exp(-value / scale)


def compute_efficiency_score(
    latency_ms: Optional[int],
    total_tokens: Optional[int],
    cost_usd: Optional[float],
    cfg: Dict,
) -> Optional[float]:
    if latency_ms is None or total_tokens is None or cost_usd is None:
        return None

    latency_ms = max(latency_ms, 1)
    latency_s = latency_ms / 1000.0
    tps = total_tokens / latency_s if latency_s > 0 else 0.0

    L0 = float(cfg.get("latency_ms", 8000))
    C0 = float(cfg.get("cost_usd", 0.2))
    T0 = float(cfg.get("tps", 50))

    w_latency = float(cfg.get("weight_latency", 0.4))
    w_cost = float(cfg.get("weight_cost", 0.4))
    w_tps = float(cfg.get("weight_tps", 0.2))
    w_sum = w_latency + w_cost + w_tps
    if w_sum <= 0:
        return None

    latency_score = _exp_score(latency_ms, L0)
    cost_score = _exp_score(cost_usd, C0)
    tps_score = _exp_score(tps, T0, invert=True)

    eff = (w_latency * latency_score + w_cost * cost_score + w_tps * tps_score) / w_sum
    return round(min(100.0, max(0.0, eff)), 2)


def compute_cost(
    input_tokens: Optional[int],
    cached_input_tokens: Optional[int],
    output_tokens: Optional[int],
    pricing: Dict,
    reasoning_tokens: Optional[int] = None,
) -> Optional[float]:
    if input_tokens is None or output_tokens is None:
        return None
    inp = pricing.get("input")
    cached_inp = pricing.get("cached_input")
    out = pricing.get("output")
    if inp is None or out is None:
        return None
    # Canonical semantics:
    # - input_tokens: non-cached input tokens
    # - cached_input_tokens: cached input tokens
    # - output_tokens: visible/non-reasoning output tokens
    # - reasoning_tokens: billed at the output rate
    cached_tokens = cached_input_tokens or 0
    reasoning = reasoning_tokens or 0
    billable_input = max(input_tokens, 0)
    cached_rate = cached_inp if cached_inp is not None else inp
    per = 1_000_000.0
    return (
        (billable_input / per) * inp
        + (cached_tokens / per) * cached_rate
        + ((output_tokens + reasoning) / per) * out
    )


def compute_final_score(
    judge_score: float, efficiency_score: Optional[float], weights: Dict
) -> float:
    judge_weight = weights.get("judge_weight", 0.8)
    efficiency_weight = weights.get("efficiency_weight", 0.2)
    eff = efficiency_score if efficiency_score is not None else 0.0
    total = judge_weight * judge_score + efficiency_weight * eff
    return round(max(0.0, min(100.0, total)), 2)

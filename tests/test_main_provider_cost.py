from __future__ import annotations

import unittest

from cli.main import compute_provider_result_cost
from providers.base import ProviderRunResult


PRICING = {"input": 1.4, "cached_input": 0.26, "output": 4.4}


def _result(aux_cost_usd: float | None) -> ProviderRunResult:
    return ProviderRunResult(
        stdout="",
        stderr="timeout",
        exit_code=124,
        elapsed_ms=1000,
        input_tokens=1_000_000,
        cached_input_tokens=500_000,
        output_tokens=100_000,
        reasoning_tokens=50_000,
        total_tokens=1_650_000,
        aux_input_tokens=100_000,
        aux_output_tokens=50_000,
        aux_cost_usd=aux_cost_usd,
        provider_cost_usd=None,
    )


class ProviderInfraCostTest(unittest.TestCase):
    def test_auxiliary_usage_is_billed_at_its_reported_cost(self) -> None:
        cost = compute_provider_result_cost(_result(0.01), PRICING)

        self.assertAlmostEqual(cost, 2.20)

    def test_auxiliary_tokens_without_reported_cost_leave_cost_unknown(self) -> None:
        self.assertIsNone(compute_provider_result_cost(_result(None), PRICING))


if __name__ == "__main__":
    unittest.main()

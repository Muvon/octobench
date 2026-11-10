# GOLD rounds — codex gpt-6.1-sol

_Generated 2026-11-10 02:43Z by `scripts/gold_rounds_report.py`; do not hand-edit._
Rounds recorded: 5. The protocol aggregate is published in
[BENCHMARK.md](../../../BENCHMARK.md) (GOLD section).

Run dates: 2026-11-08 – 2026-11-10. codex-cli 0.167.0, model gpt-6.1-sol.

Total tokens = fresh input + cache read + output (+ reasoning only where a client
reports it separately; Codex output already includes reasoning). Agent time excludes
setup, validation and judging. Unscored long-run turns are excluded from every sum.
Eff. score is the mean harness efficiency score (0-100, compute_efficiency_score:
exponential decay of agent time and cost); it is diagnostic and absolute.
Missing evidence is UNKNOWN, never zero.

## Per round

| Round | One-shots passed | Sequence turns passed | Unscored turns | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| r1 | 7/13 | 28/28 | 2 | 1.82M | 112.65M | 475.6K | 202.5K | 114.94M | $19.66 | 286.5m | 15.2 |
| r2 | 7/13 | 28/28 | 2 | 2.36M | 128.51M | 499.1K | 207.4K | 131.37M | $22.57 | 287.7m | 14.4 |
| r3 | 7/13 | 28/28 | 2 | 2.16M | 121.27M | 486.4K | 201.7K | 123.92M | $21.31 | 280.0m | 15.3 |
| r4 | 9/13 | 28/28 | 2 | 1.81M | 109.30M | 431.4K | 160.3K | 111.55M | $18.87 | 258.9m | 15.0 |
| r5 | 8/13 | 28/28 | 2 | 2.14M | 127.48M | 498.7K | 208.2K | 130.12M | $22.02 | 266.4m | 14.3 |

## Across rounds

Per item: rounds passed (sequences: scored turns passed over all rounds) and the
median over rounds of total tokens, cost and agent time, and the mean efficiency score.

| Item | Passed | Median total tokens | Median cost | Median agent time | Mean eff. score |
|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | 2/5 rounds | 10.73M | $1.70 | 23.9m | 0.0 |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | 2/5 rounds | 11.28M | $1.68 | 29.7m | 0.0 |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | 4/5 rounds | 1.59M | $0.35 | 5.0m | 10.6 |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | 0/5 rounds | 6.99M | $1.37 | 24.8m | 0.1 |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | 0/5 rounds | 17.28M | $2.63 | 27.6m | 0.0 |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | 5/5 rounds | 3.94M | $0.72 | 10.4m | 1.5 |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | 0/5 rounds | 7.31M | $1.27 | 15.1m | 0.1 |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | 5/5 rounds | 2.13M | $0.51 | 8.1m | 4.3 |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | 0/5 rounds | 1.34M | $0.36 | 5.4m | 7.5 |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | 5/5 rounds | 2.82M | $0.63 | 9.9m | 2.6 |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | 5/5 rounds | 2.60M | $0.55 | 9.6m | 2.8 |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | 5/5 rounds | 2.38M | $0.59 | 8.5m | 2.5 |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | 5/5 rounds | 2.54M | $0.52 | 6.3m | 4.5 |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 70/70 turns | 43.70M | $7.05 | 76.1m | 9.0 |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 70/70 turns | 8.39M | $1.43 | 15.7m | 31.8 |

## Round r1 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | FAIL | 239.3K | 7.77M | 26.4K | 9.8K | 8.03M | $1.52 | 24.5m | 0.0 |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | FAIL | 123.8K | 11.53M | 37.9K | 21.1K | 11.69M | $1.78 | 31.3m | 0.0 |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 27.7K | 534.1K | 4.1K | 522 | 565.9K | $0.15 | 2.3m | 23.6 |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 107.3K | 4.82M | 36.6K | 16.3K | 4.96M | $1.06 | 21.2m | 0.2 |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 157.3K | 11.41M | 53.6K | 25.8K | 11.62M | $1.99 | 32.7m | 0.0 |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 84.2K | 3.84M | 17.1K | 6.7K | 3.94M | $0.72 | 10.6m | 1.3 |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 101.6K | 5.19M | 26.6K | 7.7K | 5.32M | $0.99 | 14.8m | 0.4 |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 68.7K | 2.04M | 17.2K | 2.6K | 2.13M | $0.51 | 8.1m | 3.9 |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 47.7K | 1.49M | 11.1K | 3.4K | 1.55M | $0.36 | 6.2m | 8.4 |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 59.9K | 2.00M | 17.1K | 7.0K | 2.08M | $0.49 | 9.9m | 4.3 |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 56.1K | 2.13M | 18.8K | 5.5K | 2.20M | $0.51 | 9.8m | 3.9 |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 81.2K | 2.24M | 16.7K | 4.4K | 2.34M | $0.55 | 8.5m | 3.1 |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 70.0K | 1.60M | 11.1K | 1.9K | 1.68M | $0.41 | 6.3m | 6.4 |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 453.1K | 47.45M | 152.9K | 84.0K | 48.05M | $7.18 | 85.2m | 8.4 |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 139.2K | 8.62M | 28.5K | 5.8K | 8.79M | $1.43 | 15.2m | 32.1 |

### Round r1 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 46.1K | 1.32M | 7.1K | 2.2K | 1.37M | $0.29 | 4.6m | 11.5 |
| 2 | PASS | 49.7K | 3.57M | 11.3K | 4.3K | 3.63M | $0.57 | 6.1m | 2.9 |
| 3 | PASS | 21.6K | 2.60M | 6.5K | 2.9K | 2.63M | $0.37 | 3.5m | 7.9 |
| 4 | PASS | 57.1K | 10.75M | 28.8K | 16.4K | 10.84M | $1.48 | 15.8m | 0.0 |
| 5 | PASS | 21.7K | 4.04M | 9.8K | 6.4K | 4.07M | $0.55 | 5.3m | 3.3 |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 7 | PASS | 85.7K | 4.31M | 16.0K | 6.2K | 4.41M | $0.76 | 10.0m | 1.1 |
| 8 | PASS | 14.5K | 857.1K | 4.6K | 2.0K | 876.2K | $0.16 | 2.2m | 22.4 |
| 9 | PASS | 26.2K | 2.35M | 12.1K | 7.5K | 2.39M | $0.41 | 6.6m | 6.5 |
| 10 | PASS | 20.6K | 2.42M | 7.1K | 4.0K | 2.45M | $0.35 | 3.9m | 8.5 |
| 11 | PASS | 10.9K | 1.98M | 5.1K | 2.9K | 1.99M | $0.27 | 2.9m | 12.9 |
| 12 | PASS | 8.9K | 1.31M | 3.4K | 1.9K | 1.33M | $0.18 | 2.3m | 20.0 |
| 13 | PASS | 22.4K | 3.33M | 9.4K | 5.8K | 3.36M | $0.47 | 4.9m | 4.7 |
| 14 | PASS | 40.8K | 7.41M | 26.5K | 19.2K | 7.48M | $1.09 | 13.4m | 0.2 |
| 15 | PASS | 26.9K | 1.20M | 5.2K | 2.3K | 1.23M | $0.23 | 3.6m | 16.2 |

### Round r1 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 21.1K | 140.5K | 1.3K | 29 | 162.9K | $0.07 | 0.8m | 35.5 |
| 2 | PASS | 7.2K | 162.4K | 1.2K | 24 | 170.9K | $0.04 | 0.6m | 40.9 |
| 3 | PASS | 7.8K | 202.9K | 1.2K | 18 | 211.8K | $0.05 | 0.6m | 39.8 |
| 4 | PASS | 6.3K | 236.7K | 899 | 34 | 243.8K | $0.05 | 0.5m | 40.9 |
| 5 | PASS | 5.9K | 269.2K | 1.5K | 93 | 276.6K | $0.05 | 0.8m | 38.3 |
| 6 | PASS | 9.4K | 438.7K | 1.2K | 45 | 449.3K | $0.08 | 0.7m | 34.6 |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 8 | PASS | 7.4K | 353.5K | 1.9K | 558 | 362.9K | $0.07 | 1.0m | 35.4 |
| 9 | PASS | 12.4K | 569.1K | 1.5K | 181 | 583.0K | $0.10 | 0.8m | 30.9 |
| 10 | PASS | 7.5K | 458.6K | 1.0K | 27 | 467.1K | $0.07 | 0.6m | 35.8 |
| 11 | PASS | 5.1K | 489.9K | 1.2K | 31 | 496.1K | $0.07 | 0.8m | 35.3 |
| 12 | PASS | 18.4K | 1.47M | 4.7K | 876 | 1.50M | $0.23 | 2.5m | 15.8 |
| 13 | PASS | 7.8K | 757.2K | 3.0K | 1.2K | 768.0K | $0.12 | 1.5m | 27.2 |
| 14 | PASS | 17.7K | 2.30M | 6.0K | 2.3K | 2.32M | $0.33 | 3.1m | 9.8 |
| 15 | PASS | 5.3K | 774.9K | 1.8K | 440 | 782.0K | $0.11 | 1.0m | 29.4 |

## Round r2 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | FAIL | 141.5K | 13.12M | 36.0K | 16.9K | 13.29M | $1.96 | 23.9m | 0.0 |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | PASS | 103.3K | 7.89M | 31.0K | 16.3K | 8.03M | $1.31 | 29.7m | 0.1 |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | FAIL | 59.1K | 3.89M | 17.0K | 5.9K | 3.97M | $0.68 | 9.7m | 1.7 |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 124.2K | 6.75M | 36.4K | 17.1K | 6.91M | $1.29 | 17.7m | 0.1 |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 195.0K | 17.06M | 53.3K | 23.8K | 17.31M | $2.63 | 25.6m | 0.0 |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 68.9K | 3.56M | 14.6K | 4.1K | 3.64M | $0.64 | 8.4m | 2.0 |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 116.7K | 7.72M | 33.0K | 10.0K | 7.87M | $1.34 | 15.2m | 0.1 |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 77.0K | 3.09M | 19.3K | 3.9K | 3.19M | $0.66 | 8.7m | 1.9 |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 96.0K | 1.22M | 10.8K | 2.0K | 1.33M | $0.42 | 5.4m | 6.1 |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 77.1K | 2.72M | 20.0K | 6.8K | 2.82M | $0.63 | 9.9m | 2.2 |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 87.8K | 3.84M | 22.4K | 7.1K | 3.95M | $0.78 | 11.6m | 1.0 |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 104.5K | 2.25M | 18.1K | 7.0K | 2.38M | $0.62 | 8.1m | 2.3 |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 89.4K | 3.76M | 16.2K | 3.5K | 3.86M | $0.72 | 8.1m | 1.4 |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 886.5K | 44.34M | 145.4K | 79.6K | 45.37M | $7.66 | 92.4m | 7.7 |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 137.5K | 7.28M | 25.5K | 3.4K | 7.45M | $1.26 | 13.3m | 33.3 |

### Round r2 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 72.9K | 1.00M | 6.1K | 1.5K | 1.08M | $0.31 | 4.3m | 10.8 |
| 2 | PASS | 73.6K | 2.96M | 8.6K | 3.0K | 3.04M | $0.53 | 6.1m | 3.5 |
| 3 | PASS | 52.6K | 2.87M | 7.6K | 3.4K | 2.93M | $0.47 | 4.5m | 4.8 |
| 4 | PASS | 149.8K | 7.58M | 22.5K | 13.1K | 7.75M | $1.28 | 13.1m | 0.1 |
| 5 | PASS | 80.4K | 3.30M | 9.1K | 5.9K | 3.39M | $0.58 | 5.3m | 2.7 |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 7 | PASS | 72.7K | 7.00M | 27.2K | 17.1K | 7.10M | $1.12 | 15.6m | 0.2 |
| 8 | PASS | 21.0K | 811.5K | 3.7K | 878 | 836.3K | $0.16 | 2.6m | 22.4 |
| 9 | PASS | 32.5K | 2.56M | 11.3K | 4.8K | 2.60M | $0.43 | 8.2m | 5.7 |
| 10 | PASS | 22.0K | 1.74M | 5.2K | 2.3K | 1.77M | $0.27 | 3.7m | 12.9 |
| 11 | PASS | 13.5K | 1.81M | 4.8K | 2.1K | 1.83M | $0.26 | 2.8m | 13.9 |
| 12 | PASS | 10.1K | 1.34M | 3.6K | 2.0K | 1.35M | $0.19 | 2.7m | 19.4 |
| 13 | PASS | 23.6K | 3.28M | 7.4K | 3.8K | 3.32M | $0.45 | 5.5m | 5.3 |
| 14 | PASS | 247.0K | 5.07M | 18.8K | 13.4K | 5.33M | $1.19 | 11.7m | 0.1 |
| 15 | PASS | 14.8K | 3.02M | 9.5K | 6.4K | 3.04M | $0.43 | 6.2m | 5.9 |

### Round r2 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 25.2K | 131.1K | 1.4K | 39 | 157.7K | $0.08 | 0.8m | 34.0 |
| 2 | PASS | 7.1K | 161.8K | 1.5K | 27 | 170.4K | $0.05 | 0.7m | 40.0 |
| 3 | PASS | 5.3K | 155.0K | 906 | 0 | 161.2K | $0.04 | 0.5m | 43.3 |
| 4 | PASS | 6.5K | 225.3K | 1.1K | 42 | 232.9K | $0.05 | 0.6m | 40.4 |
| 5 | PASS | 5.9K | 257.5K | 1.6K | 84 | 265.0K | $0.05 | 0.8m | 38.5 |
| 6 | PASS | 9.1K | 360.4K | 1.4K | 47 | 371.0K | $0.07 | 0.7m | 35.7 |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 8 | PASS | 10.7K | 492.2K | 1.9K | 316 | 504.7K | $0.09 | 1.0m | 32.0 |
| 9 | PASS | 10.5K | 655.6K | 1.5K | 66 | 667.6K | $0.10 | 0.9m | 30.2 |
| 10 | PASS | 7.0K | 357.9K | 951 | 0 | 365.9K | $0.06 | 0.6m | 37.9 |
| 11 | PASS | 5.6K | 382.8K | 1.1K | 37 | 389.6K | $0.06 | 0.5m | 37.9 |
| 12 | PASS | 22.2K | 1.34M | 4.2K | 827 | 1.36M | $0.22 | 2.2m | 16.7 |
| 13 | PASS | 5.7K | 639.1K | 3.1K | 1.2K | 647.9K | $0.11 | 1.5m | 29.3 |
| 14 | PASS | 11.3K | 1.39M | 3.4K | 598 | 1.41M | $0.20 | 1.8m | 18.7 |
| 15 | PASS | 5.2K | 734.1K | 1.4K | 86 | 740.6K | $0.10 | 0.7m | 31.0 |

## Round r3 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | FAIL | 144.0K | 10.55M | 36.2K | 17.8K | 10.73M | $1.70 | 24.6m | 0.0 |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | FAIL | 104.2K | 11.14M | 35.7K | 17.3K | 11.28M | $1.68 | 27.0m | 0.0 |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 44.8K | 984.1K | 7.2K | 1.5K | 1.04M | $0.26 | 3.6m | 13.6 |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 161.2K | 8.93M | 59.7K | 35.4K | 9.15M | $1.81 | 27.9m | 0.0 |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 413.1K | 18.54M | 60.3K | 31.0K | 19.01M | $3.28 | 31.6m | 0.0 |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 96.0K | 2.46M | 14.1K | 4.1K | 2.57M | $0.58 | 10.4m | 2.8 |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 147.5K | 8.80M | 36.4K | 12.7K | 8.98M | $1.54 | 22.1m | 0.0 |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 88.6K | 2.94M | 18.4K | 4.0K | 3.05M | $0.66 | 10.1m | 1.9 |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 60.9K | 1.82M | 15.3K | 4.8K | 1.89M | $0.46 | 7.4m | 5.1 |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 69.8K | 2.45M | 20.0K | 8.7K | 2.54M | $0.58 | 9.5m | 2.7 |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 104.0K | 2.48M | 16.4K | 3.0K | 2.60M | $0.62 | 9.6m | 2.2 |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 81.4K | 2.68M | 15.9K | 4.3K | 2.78M | $0.59 | 9.2m | 2.6 |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 63.2K | 1.48M | 10.7K | 1.5K | 1.55M | $0.38 | 6.2m | 7.4 |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 438.6K | 37.81M | 109.3K | 49.6K | 38.36M | $5.75 | 64.9m | 10.2 |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 143.0K | 8.22M | 30.9K | 5.9K | 8.39M | $1.42 | 16.0m | 32.0 |

### Round r3 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 38.4K | 1.50M | 6.8K | 2.3K | 1.55M | $0.29 | 6.4m | 11.4 |
| 2 | PASS | 46.2K | 3.96M | 11.2K | 3.7K | 4.02M | $0.60 | 7.8m | 2.5 |
| 3 | PASS | 18.5K | 1.76M | 4.5K | 2.0K | 1.79M | $0.26 | 2.6m | 13.7 |
| 4 | PASS | 34.7K | 4.63M | 12.4K | 5.7K | 4.68M | $0.66 | 6.6m | 1.9 |
| 5 | PASS | 18.9K | 3.12M | 5.9K | 2.9K | 3.14M | $0.41 | 3.5m | 6.5 |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 7 | PASS | 49.5K | 8.76M | 18.0K | 9.7K | 8.82M | $1.15 | 9.2m | 0.2 |
| 8 | PASS | 17.4K | 3.32M | 6.4K | 3.7K | 3.34M | $0.43 | 3.3m | 5.8 |
| 9 | PASS | 59.2K | 1.45M | 8.6K | 2.3K | 1.52M | $0.35 | 5.8m | 8.7 |
| 10 | PASS | 61.2K | 735.9K | 3.8K | 1.6K | 800.8K | $0.23 | 2.5m | 15.5 |
| 11 | PASS | 15.3K | 908.7K | 4.3K | 1.6K | 928.3K | $0.16 | 2.1m | 21.9 |
| 12 | PASS | 7.9K | 800.6K | 2.4K | 844 | 810.9K | $0.12 | 1.8m | 27.5 |
| 13 | PASS | 21.9K | 1.73M | 5.8K | 2.8K | 1.76M | $0.28 | 3.5m | 12.6 |
| 14 | PASS | 31.1K | 2.76M | 11.7K | 6.6K | 2.80M | $0.46 | 5.5m | 5.1 |
| 15 | PASS | 18.4K | 2.38M | 7.4K | 3.8K | 2.41M | $0.35 | 4.1m | 8.7 |

### Round r3 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 17.5K | 124.2K | 1.5K | 66 | 143.2K | $0.06 | 0.9m | 36.6 |
| 2 | PASS | 7.5K | 143.2K | 1.2K | 12 | 151.9K | $0.04 | 0.6m | 41.1 |
| 3 | PASS | 7.3K | 143.0K | 977 | 24 | 151.2K | $0.04 | 0.5m | 42.1 |
| 4 | PASS | 8.3K | 223.4K | 1.2K | 43 | 232.9K | $0.05 | 0.6m | 39.2 |
| 5 | PASS | 5.2K | 256.9K | 1.4K | 103 | 263.6K | $0.05 | 0.7m | 39.1 |
| 6 | PASS | 12.4K | 433.8K | 1.7K | 63 | 447.9K | $0.08 | 0.9m | 32.8 |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 8 | PASS | 11.1K | 597.8K | 2.4K | 498 | 611.3K | $0.11 | 1.5m | 29.5 |
| 9 | PASS | 13.1K | 697.5K | 1.8K | 58 | 712.4K | $0.11 | 1.0m | 28.2 |
| 10 | PASS | 5.9K | 384.1K | 1.0K | 49 | 391.1K | $0.06 | 0.6m | 37.6 |
| 11 | PASS | 4.9K | 407.0K | 1.1K | 29 | 413.0K | $0.06 | 0.6m | 37.4 |
| 12 | PASS | 18.8K | 1.28M | 4.8K | 1.0K | 1.30M | $0.21 | 2.4m | 17.2 |
| 13 | PASS | 7.9K | 788.7K | 3.6K | 1.6K | 800.3K | $0.13 | 1.8m | 26.0 |
| 14 | PASS | 18.2K | 1.94M | 6.4K | 2.0K | 1.96M | $0.29 | 3.0m | 11.5 |
| 15 | PASS | 4.8K | 805.2K | 1.8K | 339 | 811.9K | $0.11 | 0.9m | 29.2 |

## Round r4 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | PASS | 131.1K | 7.14M | 33.7K | 16.0K | 7.31M | $1.31 | 18.7m | 0.1 |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | PASS | 93.3K | 10.01M | 22.9K | 7.9K | 10.13M | $1.42 | 22.1m | 0.0 |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 54.9K | 1.53M | 8.5K | 2.4K | 1.59M | $0.35 | 5.0m | 8.8 |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 123.7K | 6.82M | 44.4K | 21.3K | 6.99M | $1.37 | 25.7m | 0.1 |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 150.6K | 10.31M | 37.1K | 15.7K | 10.49M | $1.70 | 21.1m | 0.0 |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 94.8K | 4.53M | 18.5K | 7.8K | 4.64M | $0.83 | 10.8m | 0.8 |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 112.1K | 5.58M | 29.9K | 7.6K | 5.73M | $1.08 | 15.1m | 0.2 |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 60.0K | 1.70M | 14.6K | 2.0K | 1.77M | $0.44 | 6.8m | 5.7 |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 64.1K | 1.27M | 8.6K | 2.0K | 1.34M | $0.34 | 4.7m | 9.1 |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 62.7K | 3.40M | 17.9K | 5.3K | 3.48M | $0.64 | 10.7m | 2.0 |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 66.6K | 2.23M | 16.6K | 4.3K | 2.32M | $0.52 | 7.8m | 3.7 |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 105.3K | 4.32M | 23.3K | 8.2K | 4.45M | $0.88 | 12.9m | 0.6 |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 82.2K | 2.46M | 12.2K | 1.4K | 2.56M | $0.53 | 6.6m | 3.5 |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 398.1K | 39.33M | 113.1K | 51.8K | 39.84M | $5.86 | 75.3m | 10.6 |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 212.3K | 8.66M | 30.1K | 6.5K | 8.91M | $1.59 | 15.7m | 30.7 |

### Round r4 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 38.3K | 1.20M | 7.1K | 2.3K | 1.24M | $0.27 | 4.7m | 13.2 |
| 2 | PASS | 43.5K | 3.04M | 10.3K | 3.5K | 3.09M | $0.49 | 6.9m | 4.2 |
| 3 | PASS | 17.5K | 1.70M | 4.6K | 1.7K | 1.72M | $0.25 | 3.4m | 14.2 |
| 4 | PASS | 23.8K | 3.05M | 11.5K | 5.5K | 3.09M | $0.47 | 5.3m | 4.8 |
| 5 | PASS | 20.8K | 3.01M | 6.1K | 2.7K | 3.04M | $0.40 | 3.9m | 6.6 |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 7 | PASS | 59.4K | 9.34M | 21.9K | 12.5K | 9.42M | $1.27 | 11.2m | 0.1 |
| 8 | PASS | 50.8K | 4.09M | 10.5K | 7.1K | 4.15M | $0.62 | 5.3m | 2.3 |
| 9 | PASS | 33.8K | 1.11M | 6.1K | 2.1K | 1.15M | $0.24 | 6.4m | 15.0 |
| 10 | PASS | 25.1K | 1.30M | 4.4K | 1.1K | 1.33M | $0.22 | 4.0m | 16.3 |
| 11 | PASS | 10.2K | 1.13M | 3.5K | 1.2K | 1.14M | $0.17 | 2.9m | 21.6 |
| 12 | PASS | 8.9K | 854.7K | 2.1K | 534 | 865.6K | $0.12 | 2.9m | 26.9 |
| 13 | PASS | 17.8K | 1.92M | 5.7K | 2.3K | 1.94M | $0.28 | 4.9m | 12.1 |
| 14 | PASS | 34.7K | 5.18M | 13.9K | 6.6K | 5.23M | $0.73 | 9.0m | 1.3 |
| 15 | PASS | 13.5K | 2.41M | 5.4K | 2.7K | 2.43M | $0.32 | 4.4m | 10.0 |

### Round r4 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 20.4K | 137.9K | 1.7K | 50 | 160.0K | $0.07 | 0.9m | 35.0 |
| 2 | PASS | 6.7K | 161.5K | 1.2K | 10 | 169.4K | $0.04 | 0.6m | 41.2 |
| 3 | PASS | 8.1K | 200.1K | 1.1K | 0 | 209.3K | $0.05 | 0.6m | 40.1 |
| 4 | PASS | 6.6K | 235.1K | 920 | 39 | 242.7K | $0.05 | 0.5m | 40.9 |
| 5 | PASS | 5.0K | 267.8K | 1.4K | 210 | 274.2K | $0.05 | 0.8m | 38.8 |
| 6 | PASS | 8.0K | 302.2K | 1.3K | 29 | 311.5K | $0.06 | 0.7m | 37.4 |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 8 | PASS | 74.8K | 425.7K | 1.9K | 669 | 502.4K | $0.21 | 1.2m | 17.4 |
| 9 | PASS | 14.4K | 654.3K | 2.0K | 158 | 670.7K | $0.11 | 1.0m | 28.3 |
| 10 | PASS | 7.4K | 367.0K | 1.1K | 64 | 375.4K | $0.06 | 0.5m | 37.6 |
| 11 | PASS | 5.7K | 494.1K | 1.2K | 29 | 501.0K | $0.07 | 0.7m | 35.0 |
| 12 | PASS | 21.5K | 1.27M | 4.9K | 1.1K | 1.29M | $0.22 | 2.3m | 16.8 |
| 13 | PASS | 9.9K | 927.7K | 3.4K | 1.4K | 941.0K | $0.15 | 1.8m | 24.1 |
| 14 | PASS | 18.5K | 2.41M | 6.1K | 2.1K | 2.43M | $0.34 | 3.1m | 9.2 |
| 15 | PASS | 5.3K | 811.4K | 2.0K | 648 | 818.6K | $0.11 | 1.0m | 28.7 |

## Round r5 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | PASS | 129.5K | 11.12M | 39.6K | 20.1K | 11.29M | $1.77 | 17.6m | 0.0 |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | FAIL | 105.8K | 12.61M | 42.1K | 24.7K | 12.76M | $1.89 | 32.0m | 0.0 |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 61.7K | 2.16M | 10.4K | 3.1K | 2.24M | $0.44 | 6.5m | 5.4 |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 123.3K | 8.37M | 55.8K | 30.0K | 8.55M | $1.64 | 24.8m | 0.0 |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 206.0K | 17.02M | 51.8K | 22.9K | 17.28M | $2.63 | 27.6m | 0.0 |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 91.9K | 5.25M | 16.7K | 5.0K | 5.36M | $0.88 | 10.4m | 0.6 |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 119.3K | 7.16M | 31.6K | 10.2K | 7.31M | $1.27 | 14.3m | 0.1 |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 56.2K | 1.40M | 10.6K | 710 | 1.46M | $0.36 | 4.9m | 8.3 |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 62.2K | 1.08M | 11.1K | 2.6K | 1.15M | $0.34 | 5.4m | 9.0 |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 62.6K | 3.42M | 20.4K | 7.7K | 3.51M | $0.67 | 9.7m | 1.7 |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 59.6K | 2.63M | 16.9K | 4.6K | 2.70M | $0.55 | 8.5m | 3.2 |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 87.8K | 2.11M | 13.0K | 2.8K | 2.21M | $0.52 | 6.5m | 3.8 |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 71.8K | 2.46M | 13.0K | 2.6K | 2.54M | $0.52 | 6.3m | 3.7 |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 709.2K | 42.86M | 134.7K | 65.8K | 43.70M | $7.05 | 76.1m | 8.3 |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 194.8K | 7.83M | 31.1K | 5.3K | 8.06M | $1.48 | 15.8m | 30.8 |

### Round r5 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 61.2K | 1.53M | 9.5K | 3.4K | 1.60M | $0.37 | 5.9m | 7.8 |
| 2 | PASS | 127.5K | 3.31M | 11.6K | 4.3K | 3.45M | $0.70 | 6.1m | 1.5 |
| 3 | PASS | 31.0K | 1.92M | 5.3K | 2.2K | 1.96M | $0.31 | 2.8m | 10.8 |
| 4 | PASS | 100.0K | 7.34M | 20.7K | 11.4K | 7.46M | $1.14 | 11.2m | 0.2 |
| 5 | PASS | 75.2K | 4.38M | 11.6K | 6.8K | 4.47M | $0.70 | 5.4m | 1.5 |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 7 | PASS | 108.7K | 7.40M | 20.8K | 10.5K | 7.53M | $1.17 | 13.1m | 0.1 |
| 8 | PASS | 40.9K | 733.3K | 3.6K | 1.1K | 777.9K | $0.19 | 2.6m | 19.2 |
| 9 | PASS | 44.7K | 1.49M | 7.4K | 2.1K | 1.54M | $0.31 | 4.6m | 10.5 |
| 10 | PASS | 18.6K | 1.45M | 4.6K | 1.6K | 1.47M | $0.23 | 2.7m | 16.0 |
| 11 | PASS | 15.4K | 2.04M | 4.5K | 1.7K | 2.06M | $0.28 | 2.8m | 12.3 |
| 12 | PASS | 8.9K | 1.21M | 3.0K | 1.3K | 1.22M | $0.17 | 1.8m | 21.6 |
| 13 | PASS | 22.1K | 3.37M | 7.6K | 3.7K | 3.40M | $0.46 | 4.6m | 5.1 |
| 14 | PASS | 38.3K | 4.12M | 17.2K | 11.7K | 4.18M | $0.66 | 8.7m | 1.8 |
| 15 | PASS | 16.8K | 2.57M | 7.3K | 4.0K | 2.60M | $0.36 | 3.8m | 8.1 |

### Round r5 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 42.5K | 120.1K | 1.7K | 62 | 164.3K | $0.11 | 0.9m | 28.3 |
| 2 | PASS | 6.5K | 197.6K | 1.4K | 42 | 205.5K | $0.05 | 0.7m | 39.9 |
| 3 | PASS | 6.3K | 158.6K | 1.3K | 21 | 166.2K | $0.04 | 0.6m | 41.1 |
| 4 | PASS | 25.2K | 164.4K | 932 | 33 | 190.5K | $0.08 | 0.5m | 35.4 |
| 5 | PASS | 11.1K | 307.5K | 2.0K | 219 | 320.5K | $0.07 | 0.9m | 34.8 |
| 6 | PASS | 7.5K | 296.6K | 1.5K | 56 | 305.6K | $0.06 | 0.7m | 37.3 |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 8 | PASS | 24.7K | 546.4K | 2.2K | 386 | 573.3K | $0.13 | 1.1m | 26.6 |
| 9 | PASS | 11.4K | 654.3K | 1.7K | 69 | 667.4K | $0.11 | 1.0m | 29.6 |
| 10 | PASS | 6.0K | 357.5K | 1.3K | 33 | 364.8K | $0.06 | 0.6m | 37.5 |
| 11 | PASS | 5.1K | 382.6K | 1.3K | 34 | 389.0K | $0.06 | 0.7m | 37.2 |
| 12 | PASS | 19.9K | 1.12M | 5.8K | 1.4K | 1.14M | $0.21 | 2.8m | 17.6 |
| 13 | PASS | 7.4K | 764.9K | 2.9K | 1.1K | 775.3K | $0.12 | 1.4m | 27.4 |
| 14 | PASS | 14.8K | 1.70M | 5.1K | 1.5K | 1.72M | $0.25 | 2.7m | 14.3 |
| 15 | PASS | 6.3K | 1.07M | 2.1K | 357 | 1.08M | $0.14 | 1.2m | 24.8 |

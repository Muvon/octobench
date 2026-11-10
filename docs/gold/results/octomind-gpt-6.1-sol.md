# GOLD rounds — octomind gpt-6.1-sol

_Generated 2026-11-10 02:43Z by `scripts/gold_rounds_report.py`; do not hand-edit._
Rounds recorded: 5. The protocol aggregate is published in
[BENCHMARK.md](../../../BENCHMARK.md) (GOLD section).

Run dates: 2026-11-08 – 2026-11-10. octomind 0.70.1, model gpt-6.1-sol.

Total tokens = fresh input + cache read + output (+ reasoning only where a client
reports it separately; Codex output already includes reasoning). Agent time excludes
setup, validation and judging. Unscored long-run turns are excluded from every sum.
Eff. score is the mean harness efficiency score (0-100, compute_efficiency_score:
exponential decay of agent time and cost); it is diagnostic and absolute.
Missing evidence is UNKNOWN, never zero.

## Per round

| Round | One-shots passed | Sequence turns passed | Unscored turns | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| r1 | 7/13 | 28/28 | 2 | 2.53M | 78.66M | 263.3K | 99.5K | 81.55M | $16.77 | 282.9m | 15.8 |
| r2 | 8/13 | 28/28 | 2 | 2.48M | 72.94M | 252.9K | 86.7K | 75.76M | $15.86 | 275.8m | 16.0 |
| r3 | 8/13 | 28/28 | 2 | 2.39M | 74.26M | 248.5K | 90.5K | 76.99M | $15.80 | 293.8m | 18.0 |
| r4 | 7/13 | 28/28 | 2 | 2.48M | 72.10M | 250.5K | 100.1K | 74.93M | $15.87 | 267.4m | 16.4 |
| r5 | 8/13 | 28/28 | 2 | 2.59M | 70.57M | 250.9K | 101.3K | 73.52M | $15.97 | 279.6m | 17.3 |

## Across rounds

Per item: rounds passed (sequences: scored turns passed over all rounds) and the
median over rounds of total tokens, cost and agent time, and the mean efficiency score.

| Item | Passed | Median total tokens | Median cost | Median agent time | Mean eff. score |
|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | 3/5 rounds | 4.02M | $0.96 | 22.1m | 0.5 |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | 1/5 rounds | 4.28M | $0.88 | 39.4m | 0.6 |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | 5/5 rounds | 757.9K | $0.22 | 3.7m | 17.4 |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | 0/5 rounds | 5.42M | $1.34 | 19.7m | 0.1 |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | 0/5 rounds | 11.06M | $2.25 | 27.9m | 0.0 |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | 4/5 rounds | 2.51M | $0.55 | 11.4m | 2.5 |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | 0/5 rounds | 4.55M | $1.06 | 15.5m | 0.3 |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | 5/5 rounds | 3.27M | $0.66 | 10.5m | 2.1 |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | 0/5 rounds | 1.37M | $0.35 | 6.8m | 9.1 |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | 5/5 rounds | 2.64M | $0.68 | 10.5m | 1.8 |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | 5/5 rounds | 3.02M | $0.63 | 10.5m | 2.5 |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | 5/5 rounds | 3.02M | $0.68 | 11.0m | 2.1 |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | 5/5 rounds | 2.43M | $0.57 | 8.4m | 3.2 |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 70/70 turns | 18.42M | $3.55 | 63.9m | 15.0 |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 70/70 turns | 7.05M | $1.43 | 19.2m | 31.0 |

## Round r1 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | FAIL | 206.9K | 3.68M | 15.6K | 3.4K | 3.90M | $0.99 | 26.8m | 0.4 |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | FAIL | 187.2K | 3.81M | 13.5K | 3.3K | 4.01M | $0.93 | 24.6m | 0.5 |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 56.9K | 934.0K | 5.3K | 2.8K | 999.0K | $0.29 | 4.8m | 11.8 |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 188.8K | 7.60M | 22.1K | 14.6K | 7.82M | $1.52 | 25.4m | 0.0 |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 288.8K | 12.53M | 22.9K | 16.6K | 12.86M | $2.25 | 27.9m | 0.0 |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 88.1K | 2.41M | 8.3K | 3.7K | 2.51M | $0.54 | 9.8m | 3.4 |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 178.6K | 3.76M | 21.6K | 5.2K | 3.96M | $1.02 | 15.5m | 0.3 |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 88.0K | 3.23M | 15.7K | 2.6K | 3.34M | $0.69 | 10.5m | 1.6 |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 57.3K | 1.36M | 6.9K | 1.7K | 1.43M | $0.34 | 6.8m | 9.2 |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 144.9K | 2.75M | 13.4K | 5.3K | 2.92M | $0.77 | 13.4m | 1.1 |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 88.3K | 3.41M | 11.9K | 2.5K | 3.52M | $0.67 | 10.2m | 1.8 |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 87.9K | 4.09M | 13.4K | 4.3K | 4.19M | $0.77 | 12.3m | 1.1 |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 127.9K | 2.32M | 11.7K | 1.9K | 2.46M | $0.64 | 11.5m | 2.1 |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 483.2K | 17.86M | 54.0K | 21.6K | 18.42M | $3.55 | 60.9m | 15.5 |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 258.9K | 8.91M | 27.1K | 10.1K | 9.21M | $1.82 | 22.3m | 28.4 |

### Round r1 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 43.7K | 765.6K | 3.9K | 858 | 814.1K | $0.21 | 5.0m | 17.2 |
| 2 | PASS | 39.1K | 1.61M | 4.6K | 1.7K | 1.66M | $0.31 | 5.8m | 10.9 |
| 3 | PASS | 33.8K | 1.22M | 3.0K | 946 | 1.26M | $0.24 | 3.2m | 15.3 |
| 4 | PASS | 37.1K | 690.7K | 4.2K | 1.5K | 733.5K | $0.20 | 4.9m | 18.2 |
| 5 | PASS | 17.6K | 1.16M | 2.9K | 1.0K | 1.18M | $0.19 | 3.6m | 19.1 |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 7 | PASS | 93.2K | 2.54M | 9.6K | 3.2K | 2.65M | $0.58 | 11.4m | 2.8 |
| 8 | PASS | 24.2K | 1.23M | 3.4K | 1.6K | 1.26M | $0.22 | 3.4m | 16.2 |
| 9 | PASS | 42.2K | 863.0K | 4.5K | 2.0K | 911.6K | $0.24 | 3.9m | 14.9 |
| 10 | PASS | 26.7K | 1.13M | 2.7K | 1.1K | 1.16M | $0.20 | 2.8m | 18.0 |
| 11 | PASS | 12.3K | 1.42M | 2.7K | 1.4K | 1.44M | $0.21 | 3.4m | 17.6 |
| 12 | PASS | 12.1K | 843.3K | 1.5K | 698 | 857.6K | $0.13 | 1.5m | 26.0 |
| 13 | PASS | 58.3K | 1.35M | 4.3K | 1.8K | 1.42M | $0.32 | 4.5m | 10.2 |
| 14 | PASS | 32.3K | 1.88M | 4.1K | 3.0K | 1.92M | $0.33 | 4.7m | 9.7 |
| 15 | PASS | 10.4K | 1.14M | 2.6K | 852 | 1.16M | $0.17 | 2.7m | 21.3 |

### Round r1 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 23.9K | 94.1K | 1.1K | 18 | 119.1K | $0.07 | 0.8m | 35.5 |
| 2 | PASS | 8.0K | 198.9K | 871 | 7 | 207.8K | $0.05 | 0.8m | 40.0 |
| 3 | PASS | 10.0K | 260.2K | 856 | 0 | 271.1K | $0.06 | 0.8m | 37.9 |
| 4 | PASS | 15.2K | 397.1K | 1.0K | 25 | 413.3K | $0.08 | 1.1m | 32.8 |
| 5 | PASS | 8.0K | 491.4K | 1.8K | 155 | 501.4K | $0.09 | 1.3m | 32.6 |
| 6 | PASS | 8.0K | 419.2K | 1.2K | 102 | 428.5K | $0.07 | 0.8m | 35.1 |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 8 | PASS | 11.5K | 891.8K | 1.8K | 1.0K | 906.1K | $0.14 | 2.0m | 24.6 |
| 9 | PASS | 11.5K | 750.8K | 1.6K | 676 | 764.6K | $0.12 | 1.4m | 27.2 |
| 10 | PASS | 8.6K | 620.2K | 989 | 208 | 629.9K | $0.09 | 0.9m | 31.2 |
| 11 | PASS | 11.8K | 680.3K | 1.2K | 194 | 693.5K | $0.11 | 1.0m | 28.9 |
| 12 | PASS | 57.1K | 1.82M | 7.0K | 3.5K | 1.89M | $0.42 | 5.3m | 6.2 |
| 13 | PASS | 54.2K | 593.8K | 2.4K | 2.7K | 653.1K | $0.22 | 2.6m | 16.5 |
| 14 | PASS | 22.3K | 1.12M | 4.1K | 1.3K | 1.15M | $0.21 | 2.7m | 17.2 |
| 15 | PASS | 8.8K | 571.6K | 1.3K | 233 | 582.0K | $0.09 | 0.9m | 31.7 |

## Round r2 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | PASS | 128.5K | 3.87M | 15.2K | 2.9K | 4.02M | $0.84 | 22.1m | 0.8 |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | FAIL | 107.6K | 4.16M | 13.2K | 3.4K | 4.28M | $0.81 | 45.8m | 0.9 |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 47.6K | 704.9K | 4.2K | 1.1K | 757.9K | $0.22 | 3.6m | 16.6 |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 247.0K | 5.13M | 19.2K | 12.7K | 5.41M | $1.34 | 19.7m | 0.1 |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 235.7K | 10.19M | 13.3K | 10.5K | 10.45M | $1.75 | 19.0m | 0.0 |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 111.0K | 3.50M | 11.0K | 2.1K | 3.62M | $0.71 | 11.4m | 1.4 |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 191.8K | 5.83M | 21.0K | 6.1K | 6.05M | $1.26 | 15.8m | 0.1 |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 81.4K | 2.11M | 14.7K | 2.1K | 2.20M | $0.55 | 8.7m | 3.3 |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 66.9K | 1.07M | 8.5K | 1.6K | 1.15M | $0.35 | 6.0m | 8.8 |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 124.7K | 2.33M | 13.8K | 4.8K | 2.47M | $0.68 | 10.5m | 1.7 |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 74.8K | 2.93M | 14.8K | 4.0K | 3.02M | $0.63 | 10.5m | 2.1 |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 108.1K | 2.40M | 13.3K | 4.0K | 2.52M | $0.64 | 9.8m | 2.0 |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 87.2K | 2.56M | 11.2K | 1.9K | 2.66M | $0.57 | 8.4m | 2.9 |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 642.8K | 19.37M | 55.7K | 22.8K | 20.09M | $4.06 | 65.5m | 13.1 |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 222.7K | 6.80M | 23.8K | 6.7K | 7.05M | $1.45 | 19.2m | 31.0 |

### Round r2 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 48.6K | 1.04M | 4.9K | 851 | 1.09M | $0.26 | 4.6m | 13.6 |
| 2 | PASS | 52.4K | 1.85M | 4.4K | 1.2K | 1.91M | $0.35 | 5.3m | 8.8 |
| 3 | PASS | 30.1K | 1.42M | 2.8K | 858 | 1.45M | $0.24 | 3.3m | 14.8 |
| 4 | PASS | 54.7K | 1.61M | 6.3K | 4.5K | 1.68M | $0.38 | 6.4m | 7.3 |
| 5 | PASS | 24.8K | 1.37M | 3.1K | 1.4K | 1.40M | $0.23 | 3.2m | 15.6 |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 7 | PASS | 63.6K | 2.53M | 7.9K | 1.6K | 2.61M | $0.49 | 8.8m | 4.3 |
| 8 | PASS | 56.2K | 1.21M | 3.3K | 1.1K | 1.27M | $0.28 | 3.4m | 12.4 |
| 9 | PASS | 50.2K | 1.22M | 6.1K | 2.7K | 1.28M | $0.32 | 6.4m | 10.3 |
| 10 | PASS | 29.1K | 1.65M | 3.1K | 1.7K | 1.68M | $0.27 | 4.1m | 12.8 |
| 11 | PASS | 17.1K | 1.63M | 2.3K | 1.0K | 1.65M | $0.23 | 3.1m | 15.8 |
| 12 | PASS | 53.4K | 510.1K | 1.5K | 470 | 565.4K | $0.18 | 2.8m | 20.0 |
| 13 | PASS | 34.3K | 572.8K | 2.3K | 812 | 610.3K | $0.16 | 3.5m | 22.7 |
| 14 | PASS | 90.1K | 2.04M | 4.9K | 4.0K | 2.14M | $0.47 | 6.9m | 4.7 |
| 15 | PASS | 38.3K | 723.5K | 2.8K | 455 | 764.9K | $0.19 | 3.6m | 19.7 |

### Round r2 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 26.5K | 110.2K | 1.2K | 27 | 138.0K | $0.08 | 0.9m | 33.8 |
| 2 | PASS | 8.5K | 186.0K | 993 | 8 | 195.5K | $0.05 | 0.8m | 39.8 |
| 3 | PASS | 9.6K | 240.3K | 796 | 0 | 250.6K | $0.05 | 0.7m | 39.0 |
| 4 | PASS | 14.1K | 304.1K | 875 | 80 | 319.2K | $0.07 | 0.7m | 35.3 |
| 5 | PASS | 6.8K | 433.8K | 1.4K | 243 | 442.2K | $0.07 | 1.0m | 34.6 |
| 6 | PASS | 13.4K | 662.7K | 2.1K | 76 | 678.2K | $0.12 | 1.3m | 28.1 |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 8 | PASS | 10.6K | 874.6K | 2.2K | 1.1K | 888.6K | $0.14 | 2.0m | 24.5 |
| 9 | PASS | 29.0K | 659.2K | 2.0K | 287 | 690.5K | $0.15 | 1.5m | 23.5 |
| 10 | PASS | 22.5K | 195.2K | 1.2K | 53 | 218.9K | $0.08 | 1.0m | 33.9 |
| 11 | PASS | 5.2K | 199.0K | 1.1K | 45 | 205.4K | $0.04 | 0.8m | 40.7 |
| 12 | PASS | 25.7K | 974.2K | 3.3K | 1.1K | 1.00M | $0.20 | 2.8m | 18.8 |
| 13 | PASS | 13.4K | 500.4K | 1.8K | 1.8K | 517.3K | $0.12 | 1.9m | 28.1 |
| 14 | PASS | 27.6K | 1.32M | 3.5K | 1.7K | 1.35M | $0.24 | 2.9m | 14.9 |
| 15 | PASS | 9.9K | 139.0K | 1.3K | 258 | 150.5K | $0.05 | 1.0m | 38.9 |

## Round r3 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | PASS | 158.1K | 4.25M | 15.2K | 4.4K | 4.42M | $0.95 | 27.4m | 0.4 |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | PASS | 93.7K | 4.88M | 13.6K | 5.8K | 5.00M | $0.88 | 39.4m | 0.6 |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 32.1K | 434.8K | 3.3K | 901 | 471.2K | $0.15 | 2.7m | 23.6 |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 177.4K | 4.56M | 17.9K | 7.6K | 4.76M | $1.08 | 17.0m | 0.2 |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 411.2K | 16.54M | 26.6K | 20.5K | 17.00M | $2.99 | 36.8m | 0.0 |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | FAIL | 93.3K | 2.37M | 8.1K | 4.5K | 2.48M | $0.55 | 11.3m | 3.1 |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 180.7K | 4.35M | 20.5K | 4.4K | 4.55M | $1.06 | 17.1m | 0.2 |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 75.0K | 3.18M | 16.2K | 2.5K | 3.27M | $0.66 | 12.5m | 1.9 |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 63.0K | 1.29M | 7.9K | 2.5K | 1.37M | $0.36 | 7.8m | 8.2 |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 84.6K | 2.54M | 11.5K | 4.4K | 2.64M | $0.59 | 9.3m | 2.6 |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 88.5K | 4.02M | 14.6K | 4.1K | 4.13M | $0.77 | 13.3m | 1.0 |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 83.1K | 1.84M | 11.3K | 2.6K | 1.94M | $0.49 | 9.2m | 4.2 |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 125.9K | 2.29M | 12.2K | 2.4K | 2.43M | $0.64 | 8.7m | 2.1 |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 533.2K | 16.04M | 49.8K | 21.6K | 16.64M | $3.42 | 63.9m | 16.3 |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 193.7K | 5.67M | 19.8K | 2.2K | 5.89M | $1.19 | 17.6m | 33.0 |

### Round r3 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 67.1K | 502.3K | 3.0K | 543 | 572.9K | $0.22 | 4.3m | 16.6 |
| 2 | PASS | 36.2K | 1.39M | 3.9K | 1.2K | 1.43M | $0.26 | 5.9m | 13.3 |
| 3 | PASS | 11.2K | 1.28M | 2.6K | 769 | 1.30M | $0.19 | 3.7m | 19.7 |
| 4 | PASS | 23.3K | 1.93M | 4.3K | 1.9K | 1.96M | $0.30 | 4.4m | 11.0 |
| 5 | PASS | 59.2K | 1.09M | 3.5K | 913 | 1.16M | $0.28 | 6.0m | 12.4 |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 7 | PASS | 110.3K | 1.85M | 7.1K | 3.2K | 1.97M | $0.51 | 6.0m | 3.8 |
| 8 | PASS | 22.8K | 843.0K | 4.4K | 2.4K | 872.6K | $0.20 | 4.9m | 18.5 |
| 9 | PASS | 30.0K | 1.08M | 3.9K | 3.1K | 1.12M | $0.24 | 4.8m | 15.0 |
| 10 | PASS | 44.2K | 815.7K | 3.1K | 1.2K | 864.2K | $0.22 | 3.9m | 16.9 |
| 11 | PASS | 15.0K | 723.6K | 2.2K | 299 | 741.1K | $0.13 | 3.0m | 26.4 |
| 12 | PASS | 15.2K | 548.4K | 1.6K | 439 | 565.6K | $0.11 | 2.9m | 29.4 |
| 13 | PASS | 29.9K | 1.54M | 2.9K | 1.8K | 1.58M | $0.26 | 4.5m | 13.4 |
| 14 | PASS | 53.2K | 1.56M | 4.9K | 3.0K | 1.62M | $0.35 | 5.7m | 8.9 |
| 15 | PASS | 15.6K | 882.7K | 2.5K | 1.1K | 901.8K | $0.16 | 3.8m | 22.9 |

### Round r3 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 28.0K | 112.4K | 1.1K | 0 | 141.5K | $0.08 | 0.9m | 33.5 |
| 2 | PASS | 7.4K | 158.0K | 875 | 15 | 166.3K | $0.04 | 0.8m | 41.0 |
| 3 | PASS | 10.0K | 286.2K | 909 | 13 | 297.1K | $0.06 | 1.0m | 37.3 |
| 4 | PASS | 14.0K | 310.9K | 871 | 19 | 325.8K | $0.07 | 0.8m | 35.2 |
| 5 | PASS | 5.9K | 505.6K | 1.4K | 158 | 513.1K | $0.08 | 1.2m | 33.7 |
| 6 | PASS | 10.2K | 503.8K | 1.3K | 77 | 515.4K | $0.09 | 1.2m | 32.6 |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 8 | PASS | 8.7K | 739.1K | 1.5K | 552 | 749.8K | $0.11 | 1.9m | 28.6 |
| 9 | PASS | 23.4K | 769.2K | 1.6K | 109 | 794.2K | $0.14 | 1.4m | 24.4 |
| 10 | PASS | 32.9K | 103.0K | 1.1K | 8 | 137.0K | $0.09 | 1.0m | 32.1 |
| 11 | PASS | 6.0K | 178.4K | 1.2K | 21 | 185.6K | $0.04 | 1.1m | 40.3 |
| 12 | PASS | 19.4K | 543.7K | 2.7K | 359 | 566.2K | $0.12 | 2.1m | 26.8 |
| 13 | PASS | 10.6K | 389.0K | 1.5K | 374 | 401.5K | $0.08 | 1.4m | 33.6 |
| 14 | PASS | 11.7K | 615.3K | 2.5K | 369 | 629.9K | $0.11 | 1.8m | 28.2 |
| 15 | PASS | 5.6K | 456.2K | 1.1K | 81 | 463.0K | $0.07 | 1.0m | 35.4 |

## Round r4 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | FAIL | 179.8K | 3.80M | 14.4K | 5.7K | 4.00M | $0.96 | 21.3m | 0.4 |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | FAIL | 123.4K | 4.99M | 14.1K | 5.2K | 5.13M | $0.94 | 24.0m | 0.4 |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 37.1K | 459.3K | 3.3K | 1.3K | 500.9K | $0.17 | 5.1m | 21.7 |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 262.9K | 5.13M | 16.6K | 5.9K | 5.42M | $1.28 | 16.5m | 0.1 |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 238.0K | 6.19M | 17.4K | 13.5K | 6.46M | $1.42 | 20.1m | 0.0 |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 83.3K | 2.26M | 9.5K | 2.9K | 2.35M | $0.52 | 12.5m | 3.7 |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 155.9K | 3.90M | 15.7K | 2.7K | 4.07M | $0.90 | 14.5m | 0.6 |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 117.9K | 3.46M | 15.3K | 2.5K | 3.59M | $0.77 | 11.2m | 1.1 |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 58.7K | 1.34M | 8.4K | 3.3K | 1.41M | $0.37 | 7.2m | 7.8 |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 118.7K | 4.49M | 14.3K | 7.2K | 4.63M | $0.92 | 13.0m | 0.5 |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 66.1K | 2.11M | 11.4K | 1.9K | 2.19M | $0.48 | 8.8m | 4.6 |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 113.9K | 2.96M | 13.8K | 4.1K | 3.10M | $0.71 | 13.0m | 1.4 |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 69.8K | 2.22M | 10.1K | 1.4K | 2.30M | $0.48 | 7.6m | 4.5 |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 647.5K | 21.55M | 62.9K | 39.0K | 22.30M | $4.53 | 76.4m | 13.5 |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 204.2K | 7.25M | 23.3K | 3.6K | 7.48M | $1.43 | 16.3m | 31.3 |

### Round r4 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 34.6K | 540.5K | 3.3K | 806 | 579.3K | $0.17 | 7.8m | 21.5 |
| 2 | PASS | 24.9K | 1.02M | 3.3K | 1.3K | 1.05M | $0.20 | 3.9m | 18.4 |
| 3 | PASS | 21.7K | 1.59M | 3.2K | 1.2K | 1.62M | $0.25 | 3.2m | 14.4 |
| 4 | PASS | 74.4K | 2.57M | 8.3K | 7.2K | 2.66M | $0.57 | 10.2m | 2.9 |
| 5 | PASS | 109.8K | 2.40M | 3.8K | 3.4K | 2.52M | $0.54 | 4.5m | 3.4 |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 7 | PASS | 113.9K | 2.40M | 10.5K | 4.1K | 2.53M | $0.63 | 8.2m | 2.1 |
| 8 | PASS | 17.6K | 589.6K | 2.6K | 1.3K | 611.0K | $0.13 | 2.6m | 25.5 |
| 9 | PASS | 30.3K | 1.87M | 4.2K | 3.0K | 1.91M | $0.32 | 5.1m | 10.0 |
| 10 | PASS | 68.1K | 2.03M | 6.3K | 3.7K | 2.11M | $0.44 | 6.8m | 5.4 |
| 11 | PASS | 14.5K | 1.22M | 2.5K | 969 | 1.24M | $0.19 | 2.6m | 19.6 |
| 12 | PASS | 11.8K | 713.6K | 1.4K | 293 | 727.1K | $0.11 | 1.6m | 28.4 |
| 13 | PASS | 55.6K | 1.18M | 4.2K | 2.1K | 1.24M | $0.30 | 5.5m | 11.3 |
| 14 | PASS | 41.2K | 2.85M | 5.9K | 8.7K | 2.90M | $0.52 | 10.3m | 3.7 |
| 15 | PASS | 29.0K | 563.7K | 3.4K | 987 | 597.2K | $0.16 | 4.0m | 22.4 |

### Round r4 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 30.0K | 169.9K | 1.4K | 22 | 201.3K | $0.09 | 1.0m | 31.3 |
| 2 | PASS | 9.9K | 209.3K | 1.1K | 7 | 220.2K | $0.05 | 0.7m | 38.9 |
| 3 | PASS | 10.5K | 225.2K | 730 | 18 | 236.4K | $0.05 | 0.6m | 39.2 |
| 4 | PASS | 15.8K | 418.6K | 958 | 65 | 435.4K | $0.09 | 0.8m | 32.4 |
| 5 | PASS | 8.5K | 573.2K | 1.4K | 195 | 583.3K | $0.09 | 1.0m | 31.6 |
| 6 | PASS | 15.7K | 753.7K | 1.6K | 73 | 771.0K | $0.12 | 1.0m | 26.9 |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 8 | PASS | 7.9K | 873.0K | 1.5K | 461 | 882.7K | $0.13 | 1.3m | 26.7 |
| 9 | PASS | 16.2K | 112.8K | 1.2K | 34 | 130.2K | $0.06 | 0.8m | 37.6 |
| 10 | PASS | 22.1K | 90.2K | 836 | 19 | 113.2K | $0.06 | 0.6m | 37.2 |
| 11 | PASS | 6.5K | 162.6K | 991 | 42 | 170.1K | $0.04 | 0.6m | 41.2 |
| 12 | PASS | 22.7K | 1.15M | 5.0K | 756 | 1.18M | $0.22 | 3.1m | 16.6 |
| 13 | PASS | 9.1K | 550.1K | 1.7K | 617 | 561.5K | $0.10 | 1.3m | 30.7 |
| 14 | PASS | 24.3K | 1.34M | 3.5K | 855 | 1.37M | $0.23 | 2.4m | 15.9 |
| 15 | PASS | 5.1K | 619.0K | 1.5K | 403 | 626.0K | $0.09 | 1.1m | 31.2 |

## Round r5 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | PASS | 186.6K | 4.28M | 13.1K | 4.5K | 4.48M | $0.99 | 20.7m | 0.3 |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | FAIL | 126.0K | 3.78M | 15.3K | 6.1K | 3.93M | $0.86 | 39.4m | 0.7 |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 55.9K | 1.02M | 4.3K | 1.1K | 1.08M | $0.27 | 3.7m | 13.1 |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 318.6K | 6.59M | 22.0K | 17.5K | 6.95M | $1.71 | 23.5m | 0.0 |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 364.6K | 10.65M | 24.7K | 19.6K | 11.06M | $2.25 | 30.6m | 0.0 |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 152.6K | 3.72M | 12.0K | 4.6K | 3.89M | $0.85 | 12.0m | 0.7 |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 182.6K | 4.60M | 20.8K | 4.1K | 4.80M | $1.09 | 14.4m | 0.2 |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 90.7K | 2.42M | 14.0K | 2.4K | 2.53M | $0.59 | 9.1m | 2.6 |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 50.9K | 1.10M | 6.7K | 1.4K | 1.15M | $0.30 | 5.5m | 11.3 |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 81.8K | 2.33M | 10.9K | 4.4K | 2.42M | $0.55 | 7.9m | 3.1 |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 68.1K | 2.55M | 13.3K | 2.6K | 2.63M | $0.55 | 14.6m | 3.1 |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 102.8K | 2.90M | 12.2K | 5.3K | 3.02M | $0.68 | 11.0m | 1.6 |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 79.0K | 2.17M | 10.0K | 1.4K | 2.26M | $0.49 | 6.7m | 4.2 |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 491.7K | 16.69M | 47.7K | 18.3K | 17.25M | $3.37 | 61.0m | 16.6 |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 243.0K | 5.78M | 23.8K | 7.9K | 6.05M | $1.41 | 19.2m | 31.3 |

### Round r5 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 38.2K | 578.6K | 3.2K | 955 | 621.0K | $0.18 | 3.3m | 20.4 |
| 2 | PASS | 31.1K | 1.37M | 3.9K | 576 | 1.40M | $0.25 | 4.4m | 14.6 |
| 3 | PASS | 15.9K | 1.32M | 2.6K | 617 | 1.34M | $0.20 | 2.7m | 18.6 |
| 4 | PASS | 44.0K | 1.09M | 3.7K | 1.6K | 1.14M | $0.25 | 4.2m | 14.0 |
| 5 | PASS | 54.0K | 1.03M | 2.8K | 923 | 1.09M | $0.25 | 3.5m | 14.2 |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 7 | PASS | 81.1K | 2.68M | 7.8K | 2.6K | 2.77M | $0.54 | 8.2m | 3.3 |
| 8 | PASS | 16.0K | 748.8K | 2.4K | 1.1K | 768.3K | $0.14 | 2.2m | 24.4 |
| 9 | PASS | 18.9K | 1.85M | 4.3K | 3.4K | 1.88M | $0.30 | 4.6m | 10.9 |
| 10 | PASS | 63.3K | 1.32M | 4.2K | 2.5K | 1.39M | $0.33 | 6.5m | 9.5 |
| 11 | PASS | 39.2K | 842.4K | 2.6K | 485 | 884.7K | $0.20 | 4.7m | 18.7 |
| 12 | PASS | 14.0K | 712.6K | 2.0K | 520 | 729.1K | $0.13 | 3.9m | 26.6 |
| 13 | PASS | 18.9K | 1.40M | 2.7K | 1.4K | 1.42M | $0.22 | 5.1m | 16.4 |
| 14 | PASS | 37.9K | 1.04M | 2.7K | 943 | 1.08M | $0.22 | 3.9m | 16.6 |
| 15 | PASS | 19.1K | 695.8K | 2.8K | 677 | 718.4K | $0.15 | 3.7m | 24.1 |

### Round r5 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time | Eff. score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 33.5K | 151.8K | 1.5K | 48 | 186.8K | $0.10 | 0.9m | 30.2 |
| 2 | PASS | 8.1K | 227.8K | 1.0K | 34 | 237.0K | $0.05 | 0.8m | 38.9 |
| 3 | PASS | 10.9K | 233.1K | 858 | 26 | 244.9K | $0.06 | 0.7m | 38.1 |
| 4 | PASS | 13.6K | 289.0K | 817 | 10 | 303.4K | $0.07 | 0.8m | 35.8 |
| 5 | PASS | 5.0K | 416.0K | 1.4K | 65 | 422.4K | $0.07 | 0.8m | 36.0 |
| 6 | PASS | 9.4K | 546.4K | 1.4K | 96 | 557.4K | $0.09 | 0.9m | 32.0 |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — | — |
| 8 | PASS | 9.2K | 703.7K | 1.8K | 578 | 715.3K | $0.11 | 1.5m | 28.4 |
| 9 | PASS | 22.5K | 429.3K | 1.4K | 137 | 453.3K | $0.11 | 1.1m | 29.4 |
| 10 | PASS | 22.6K | 112.9K | 912 | 73 | 136.4K | $0.07 | 0.7m | 36.1 |
| 11 | PASS | 7.1K | 166.9K | 1.1K | 55 | 175.2K | $0.04 | 0.7m | 40.6 |
| 12 | PASS | 26.6K | 1.03M | 4.2K | 2.5K | 1.06M | $0.22 | 3.6m | 16.3 |
| 13 | PASS | 17.2K | 465.3K | 1.7K | 2.4K | 486.6K | $0.13 | 2.4m | 26.6 |
| 14 | PASS | 43.0K | 630.4K | 3.9K | 1.7K | 679.0K | $0.21 | 3.1m | 17.6 |
| 15 | PASS | 14.3K | 377.6K | 1.9K | 202 | 393.9K | $0.09 | 1.3m | 31.9 |

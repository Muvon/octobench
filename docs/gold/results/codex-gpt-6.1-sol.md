# GOLD rounds — codex gpt-6.1-sol

_Generated 2026-10-17 10:26Z by `scripts/gold_rounds_report.py`; do not hand-edit._
Rounds recorded: 5. The protocol aggregate is published in
[BENCHMARK.md](../../../BENCHMARK.md) (GOLD section).

Total tokens = fresh input + cache read + output (+ reasoning only where a client
reports it separately; Codex output already includes reasoning). Agent time excludes
setup, validation and judging. Unscored long-run turns are excluded from every sum.
Missing evidence is UNKNOWN, never zero.

## Per round

| Round | One-shots passed | Sequence turns passed | Unscored turns | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|---|---|
| r1 | 8/13 | 28/28 | 2 | 2.18M | 90.04M | 424.1K | 151.5K | 92.64M | $17.60 | 238.5m |
| r2 | 9/13 | 28/28 | 2 | 2.33M | 94.69M | 436.0K | 150.5K | 97.46M | $18.49 | 218.0m |
| r3 | 7/13 | 28/28 | 2 | 2.28M | 95.21M | 424.6K | 147.8K | 97.91M | $18.33 | 205.2m |
| r4 | 9/13 | 28/28 | 2 | 2.45M | 104.34M | 463.3K | 166.9K | 107.25M | $19.96 | 209.7m |
| r5 | 8/13 | 28/28 | 2 | 2.74M | 97.54M | 430.9K | 154.2K | 100.71M | $19.54 | 201.6m |

## Across rounds

Per item: rounds passed (sequences: scored turns passed over all rounds) and the
median over rounds of total tokens, cost and agent time.

| Item | Passed | Median total tokens | Median cost | Median agent time |
|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | 2/5 rounds | 8.30M | $1.39 | 17.0m |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | 5/5 rounds | 8.16M | $1.53 | 22.8m |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | 5/5 rounds | 1.66M | $0.38 | 3.8m |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | 0/5 rounds | 6.79M | $1.36 | 17.5m |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | 0/5 rounds | 11.85M | $2.14 | 22.5m |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | 5/5 rounds | 3.14M | $0.64 | 6.2m |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | 0/5 rounds | 8.82M | $1.66 | 15.7m |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | 5/5 rounds | 2.15M | $0.57 | 6.3m |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | 0/5 rounds | 1.42M | $0.36 | 4.6m |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | 5/5 rounds | 2.77M | $0.64 | 7.4m |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | 4/5 rounds | 2.83M | $0.68 | 7.6m |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | 5/5 rounds | 1.93M | $0.53 | 6.5m |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | 5/5 rounds | 1.93M | $0.49 | 5.2m |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 70/70 turns | 27.44M | $4.77 | 59.7m |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 70/70 turns | 7.35M | $1.41 | 12.1m |

## Round r1 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | FAIL | 158.6K | 8.11M | 28.2K | 11.8K | 8.30M | $1.41 | 18.9m |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | PASS | 178.7K | 9.25M | 37.5K | 20.9K | 9.46M | $1.66 | 27.2m |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 47.2K | 942.6K | 7.2K | 2.0K | 997.0K | $0.26 | 3.4m |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 137.8K | 5.68M | 31.6K | 12.9K | 5.85M | $1.16 | 17.7m |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 274.4K | 9.66M | 43.2K | 15.8K | 9.98M | $1.95 | 22.5m |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 83.6K | 2.30M | 12.6K | 4.1K | 2.40M | $0.52 | 6.2m |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 180.4K | 10.28M | 44.9K | 18.3K | 10.50M | $1.84 | 20.7m |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 79.5K | 2.06M | 15.5K | 2.6K | 2.15M | $0.52 | 5.8m |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 94.8K | 2.01M | 14.2K | 3.8K | 2.12M | $0.53 | 6.5m |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 73.4K | 2.22M | 15.3K | 4.9K | 2.30M | $0.52 | 7.4m |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 88.6K | 2.49M | 21.5K | 6.8K | 2.60M | $0.64 | 9.4m |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 86.7K | 1.82M | 17.8K | 4.6K | 1.93M | $0.53 | 8.3m |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 90.7K | 2.71M | 13.8K | 2.3K | 2.81M | $0.59 | 7.0m |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 448.3K | 24.25M | 93.7K | 35.7K | 24.79M | $4.26 | 64.2m |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 153.3K | 6.26M | 27.1K | 5.1K | 6.44M | $1.20 | 13.1m |

### Round r1 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 44.4K | 712.2K | 4.7K | 789 | 761.3K | $0.21 | 3.1m |
| 2 | PASS | 37.3K | 2.09M | 5.4K | 1.1K | 2.13M | $0.34 | 4.7m |
| 3 | PASS | 21.1K | 1.29M | 3.6K | 1.3K | 1.31M | $0.21 | 3.4m |
| 4 | PASS | 46.3K | 4.33M | 12.9K | 5.7K | 4.38M | $0.65 | 9.1m |
| 5 | PASS | 32.2K | 920.8K | 3.7K | 705 | 956.7K | $0.19 | 4.1m |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — |
| 7 | PASS | 63.8K | 3.32M | 14.7K | 5.7K | 3.40M | $0.61 | 9.2m |
| 8 | PASS | 25.2K | 1.71M | 6.2K | 3.0K | 1.74M | $0.28 | 3.7m |
| 9 | PASS | 32.6K | 2.12M | 10.3K | 5.6K | 2.16M | $0.38 | 5.6m |
| 10 | PASS | 32.0K | 791.6K | 3.9K | 318 | 827.5K | $0.18 | 4.0m |
| 11 | PASS | 17.3K | 943.1K | 4.2K | 1.1K | 964.5K | $0.17 | 2.9m |
| 12 | PASS | 14.0K | 819.6K | 3.1K | 1.0K | 836.7K | $0.14 | 2.6m |
| 13 | PASS | 23.6K | 1.35M | 5.4K | 1.8K | 1.38M | $0.24 | 3.5m |
| 14 | PASS | 41.4K | 2.05M | 9.9K | 5.2K | 2.10M | $0.39 | 5.0m |
| 15 | PASS | 17.1K | 1.80M | 5.6K | 2.3K | 1.82M | $0.27 | 3.3m |

### Round r1 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 17.8K | 139.0K | 1.5K | 27 | 158.3K | $0.06 | 0.9m |
| 2 | PASS | 6.5K | 108.0K | 875 | 9 | 115.4K | $0.03 | 0.5m |
| 3 | PASS | 7.3K | 132.9K | 764 | 0 | 140.9K | $0.04 | 0.4m |
| 4 | PASS | 6.7K | 197.4K | 858 | 8 | 205.0K | $0.04 | 0.5m |
| 5 | PASS | 4.2K | 176.3K | 1.2K | 62 | 181.7K | $0.04 | 0.6m |
| 6 | PASS | 10.4K | 253.3K | 1.4K | 32 | 265.1K | $0.06 | 0.6m |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — |
| 8 | PASS | 9.8K | 361.7K | 1.9K | 395 | 373.5K | $0.08 | 1.0m |
| 9 | PASS | 12.0K | 421.4K | 1.5K | 258 | 434.9K | $0.08 | 0.9m |
| 10 | PASS | 6.5K | 313.2K | 855 | 19 | 320.6K | $0.05 | 0.5m |
| 11 | PASS | 6.2K | 335.5K | 1.0K | 12 | 342.8K | $0.06 | 0.5m |
| 12 | PASS | 26.9K | 1.11M | 5.7K | 1.6K | 1.14M | $0.22 | 2.6m |
| 13 | PASS | 11.7K | 702.3K | 3.4K | 1.3K | 717.5K | $0.13 | 1.6m |
| 14 | PASS | 22.7K | 1.45M | 4.7K | 1.2K | 1.47M | $0.24 | 2.1m |
| 15 | PASS | 4.5K | 564.1K | 1.3K | 242 | 569.9K | $0.08 | 0.7m |

## Round r2 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | PASS | 128.4K | 5.64M | 24.9K | 9.8K | 5.79M | $1.07 | 12.9m |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | PASS | 135.2K | 7.53M | 27.6K | 11.2K | 7.69M | $1.30 | 22.8m |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 38.1K | 767.6K | 6.2K | 1.3K | 811.9K | $0.21 | 3.3m |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 154.2K | 6.59M | 38.9K | 17.6K | 6.79M | $1.36 | 17.5m |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 372.2K | 15.77M | 67.6K | 31.6K | 16.21M | $3.00 | 31.4m |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 115.1K | 4.25M | 17.0K | 5.9K | 4.38M | $0.82 | 9.6m |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 214.7K | 8.57M | 37.0K | 10.3K | 8.82M | $1.66 | 15.7m |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 70.6K | 1.77M | 14.3K | 2.0K | 1.86M | $0.46 | 6.3m |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 84.2K | 2.28M | 15.0K | 4.8K | 2.38M | $0.55 | 6.7m |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 86.8K | 2.66M | 19.7K | 7.0K | 2.77M | $0.64 | 8.8m |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 81.2K | 2.22M | 15.1K | 2.9K | 2.32M | $0.54 | 7.4m |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 69.6K | 1.32M | 10.3K | 1.5K | 1.40M | $0.37 | 5.0m |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 72.1K | 1.57M | 9.1K | 766 | 1.65M | $0.39 | 4.5m |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 541.7K | 26.80M | 103.1K | 38.4K | 27.44M | $4.79 | 53.8m |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 167.9K | 6.96M | 30.3K | 5.7K | 7.16M | $1.34 | 12.1m |

### Round r2 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 42.2K | 932.1K | 4.8K | 972 | 979.1K | $0.23 | 3.3m |
| 2 | PASS | 48.9K | 3.07M | 9.2K | 2.9K | 3.12M | $0.50 | 5.3m |
| 3 | PASS | 28.3K | 2.32M | 5.6K | 1.9K | 2.35M | $0.34 | 2.8m |
| 4 | PASS | 77.3K | 5.26M | 15.2K | 6.3K | 5.35M | $0.83 | 8.1m |
| 5 | PASS | 39.0K | 720.0K | 4.0K | 916 | 763.0K | $0.19 | 2.3m |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — |
| 7 | PASS | 79.6K | 3.54M | 17.3K | 7.5K | 3.64M | $0.69 | 7.8m |
| 8 | PASS | 26.1K | 1.47M | 6.0K | 3.0K | 1.50M | $0.26 | 2.5m |
| 9 | PASS | 36.5K | 676.1K | 5.4K | 1.4K | 718.0K | $0.19 | 3.6m |
| 10 | PASS | 29.6K | 967.9K | 5.3K | 1.2K | 1.00M | $0.21 | 2.6m |
| 11 | PASS | 13.9K | 770.0K | 3.2K | 853 | 787.1K | $0.14 | 1.6m |
| 12 | PASS | 12.2K | 906.9K | 2.8K | 963 | 921.9K | $0.14 | 1.6m |
| 13 | PASS | 24.8K | 1.78M | 6.0K | 2.5K | 1.81M | $0.29 | 3.1m |
| 14 | PASS | 62.3K | 3.76M | 14.7K | 7.5K | 3.83M | $0.65 | 7.1m |
| 15 | PASS | 21.0K | 631.0K | 3.6K | 443 | 655.6K | $0.14 | 2.1m |

### Round r2 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 27.1K | 131.3K | 2.0K | 45 | 160.4K | $0.09 | 0.8m |
| 2 | PASS | 7.4K | 127.4K | 1.1K | 7 | 135.8K | $0.04 | 0.4m |
| 3 | PASS | 10.4K | 159.7K | 1.2K | 8 | 171.3K | $0.05 | 0.4m |
| 4 | PASS | 9.0K | 247.7K | 1.1K | 33 | 257.8K | $0.05 | 0.5m |
| 5 | PASS | 6.3K | 336.0K | 1.8K | 141 | 344.1K | $0.06 | 0.7m |
| 6 | PASS | 9.7K | 315.4K | 1.3K | 17 | 326.4K | $0.06 | 0.5m |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — |
| 8 | PASS | 11.5K | 434.8K | 2.3K | 483 | 448.6K | $0.09 | 1.0m |
| 9 | PASS | 12.2K | 500.0K | 1.5K | 25 | 513.7K | $0.09 | 0.7m |
| 10 | PASS | 6.1K | 458.5K | 1.2K | 31 | 465.8K | $0.07 | 0.5m |
| 11 | PASS | 5.3K | 481.2K | 1.0K | 0 | 487.5K | $0.07 | 0.5m |
| 12 | PASS | 29.3K | 1.22M | 6.0K | 1.3K | 1.26M | $0.24 | 2.2m |
| 13 | PASS | 9.2K | 646.5K | 2.9K | 1.2K | 658.7K | $0.11 | 1.2m |
| 14 | PASS | 19.8K | 1.29M | 5.2K | 1.8K | 1.31M | $0.22 | 2.0m |
| 15 | PASS | 4.7K | 615.9K | 1.7K | 498 | 622.4K | $0.09 | 0.7m |

## Round r3 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | FAIL | 174.7K | 10.00M | 34.6K | 17.1K | 10.21M | $1.70 | 15.6m |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | PASS | 117.5K | 7.45M | 23.9K | 8.5K | 7.59M | $1.22 | 23.5m |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 102.8K | 1.55M | 8.3K | 2.0K | 1.66M | $0.44 | 3.8m |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 163.5K | 6.95M | 41.0K | 18.3K | 7.16M | $1.43 | 16.6m |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 186.7K | 9.01M | 41.6K | 17.8K | 9.24M | $1.69 | 14.4m |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 104.0K | 2.65M | 12.4K | 2.7K | 2.76M | $0.60 | 5.4m |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 164.8K | 6.80M | 33.9K | 10.6K | 7.00M | $1.35 | 12.4m |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 90.8K | 2.65M | 20.9K | 4.8K | 2.76M | $0.66 | 7.2m |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 61.1K | 1.35M | 10.5K | 1.6K | 1.42M | $0.36 | 4.6m |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 78.1K | 2.74M | 18.3K | 6.5K | 2.84M | $0.61 | 8.0m |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | FAIL | 107.4K | 2.80M | 18.9K | 5.4K | 2.92M | $0.68 | 7.2m |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 118.3K | 2.68M | 22.0K | 8.3K | 2.82M | $0.73 | 8.9m |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 94.8K | 1.76M | 12.4K | 1.8K | 1.86M | $0.49 | 5.2m |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 475.1K | 28.70M | 94.5K | 36.4K | 29.27M | $4.77 | 59.7m |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 242.0K | 8.12M | 31.4K | 6.1K | 8.40M | $1.61 | 12.8m |

### Round r3 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 49.9K | 1.46M | 6.2K | 1.3K | 1.52M | $0.31 | 4.3m |
| 2 | PASS | 32.4K | 2.28M | 5.6K | 1.6K | 2.32M | $0.35 | 4.0m |
| 3 | PASS | 22.1K | 1.60M | 4.3K | 1.4K | 1.63M | $0.25 | 3.0m |
| 4 | PASS | 29.6K | 2.22M | 7.5K | 2.5K | 2.26M | $0.36 | 3.3m |
| 5 | PASS | 22.7K | 2.27M | 5.9K | 2.7K | 2.30M | $0.33 | 3.0m |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — |
| 7 | PASS | 91.5K | 4.01M | 17.1K | 7.0K | 4.12M | $0.76 | 8.5m |
| 8 | PASS | 27.6K | 1.79M | 6.8K | 3.3K | 1.82M | $0.30 | 3.1m |
| 9 | PASS | 62.7K | 2.61M | 11.1K | 6.0K | 2.68M | $0.50 | 5.9m |
| 10 | PASS | 22.6K | 667.9K | 3.3K | 540 | 693.8K | $0.14 | 3.0m |
| 11 | PASS | 11.1K | 688.3K | 2.6K | 530 | 701.9K | $0.12 | 2.2m |
| 12 | PASS | 10.0K | 615.7K | 1.8K | 306 | 627.5K | $0.10 | 2.5m |
| 13 | PASS | 27.5K | 1.71M | 4.8K | 1.8K | 1.74M | $0.27 | 4.7m |
| 14 | PASS | 44.6K | 3.49M | 11.7K | 5.3K | 3.54M | $0.56 | 7.0m |
| 15 | PASS | 20.9K | 3.29M | 5.7K | 2.1K | 3.31M | $0.43 | 5.1m |

### Round r3 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 29.5K | 173.1K | 1.9K | 17 | 204.4K | $0.10 | 0.8m |
| 2 | PASS | 7.4K | 121.1K | 1.0K | 7 | 129.5K | $0.04 | 0.3m |
| 3 | PASS | 8.0K | 148.9K | 904 | 0 | 157.7K | $0.04 | 0.4m |
| 4 | PASS | 6.9K | 221.4K | 907 | 16 | 229.2K | $0.05 | 0.4m |
| 5 | PASS | 54.9K | 266.2K | 1.5K | 97 | 322.6K | $0.15 | 1.0m |
| 6 | PASS | 9.8K | 299.9K | 1.5K | 43 | 311.2K | $0.07 | 0.5m |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — |
| 8 | PASS | 10.1K | 345.6K | 1.8K | 461 | 357.5K | $0.07 | 0.7m |
| 9 | PASS | 11.5K | 555.9K | 1.8K | 151 | 569.1K | $0.10 | 0.7m |
| 10 | PASS | 7.2K | 346.9K | 879 | 0 | 355.0K | $0.06 | 0.4m |
| 11 | PASS | 5.9K | 369.5K | 1.2K | 29 | 376.6K | $0.06 | 0.5m |
| 12 | PASS | 36.3K | 2.04M | 7.2K | 1.9K | 2.08M | $0.35 | 2.5m |
| 13 | PASS | 10.9K | 934.7K | 3.3K | 1.3K | 948.9K | $0.15 | 1.2m |
| 14 | PASS | 23.2K | 2.09M | 6.4K | 2.1K | 2.12M | $0.32 | 2.3m |
| 15 | PASS | 20.5K | 213.2K | 1.1K | 48 | 234.9K | $0.07 | 1.2m |

## Round r4 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | PASS | 139.1K | 6.48M | 34.4K | 18.6K | 6.65M | $1.27 | 18.1m |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | PASS | 157.3K | 12.57M | 37.0K | 17.6K | 12.76M | $1.94 | 21.8m |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 57.5K | 1.75M | 9.3K | 2.5K | 1.82M | $0.38 | 3.9m |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 143.1K | 4.42M | 31.8K | 13.0K | 4.59M | $1.05 | 11.2m |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 368.5K | 15.71M | 61.1K | 25.4K | 16.14M | $2.92 | 23.9m |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 97.2K | 3.03M | 14.3K | 4.3K | 3.14M | $0.64 | 5.4m |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 136.8K | 6.44M | 29.8K | 9.4K | 6.61M | $1.22 | 9.0m |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 153.9K | 4.35M | 23.8K | 4.9K | 4.52M | $0.98 | 12.3m |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 52.1K | 896.5K | 8.0K | 872 | 956.7K | $0.27 | 2.8m |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 100.2K | 3.45M | 21.8K | 8.3K | 3.57M | $0.76 | 7.4m |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 96.1K | 2.71M | 21.5K | 6.4K | 2.83M | $0.68 | 7.6m |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 69.8K | 1.40M | 13.7K | 4.4K | 1.48M | $0.42 | 4.5m |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 138.4K | 2.76M | 15.3K | 2.7K | 2.92M | $0.71 | 5.4m |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 542.0K | 31.25M | 110.6K | 41.6K | 31.90M | $5.31 | 65.4m |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 193.2K | 7.13M | 30.8K | 7.0K | 7.35M | $1.41 | 11.1m |

### Round r4 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 41.7K | 1.07M | 5.8K | 942 | 1.12M | $0.25 | 3.2m |
| 2 | PASS | 46.7K | 3.26M | 8.9K | 2.1K | 3.32M | $0.51 | 5.4m |
| 3 | PASS | 25.0K | 2.12M | 4.9K | 1.2K | 2.15M | $0.31 | 2.5m |
| 4 | PASS | 36.5K | 3.83M | 8.8K | 3.2K | 3.87M | $0.54 | 3.4m |
| 5 | PASS | 29.8K | 1.08M | 5.5K | 2.0K | 1.12M | $0.22 | 2.8m |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — |
| 7 | PASS | 100.6K | 4.23M | 16.8K | 6.5K | 4.34M | $0.79 | 9.3m |
| 8 | PASS | 28.7K | 2.62M | 9.5K | 4.8K | 2.65M | $0.41 | 7.3m |
| 9 | PASS | 50.0K | 1.69M | 9.8K | 3.6K | 1.75M | $0.37 | 7.5m |
| 10 | PASS | 32.5K | 1.41M | 4.9K | 880 | 1.45M | $0.25 | 3.3m |
| 11 | PASS | 12.7K | 936.2K | 2.9K | 878 | 951.8K | $0.15 | 2.1m |
| 12 | PASS | 15.7K | 1.11M | 2.5K | 653 | 1.12M | $0.17 | 2.5m |
| 13 | PASS | 21.9K | 2.02M | 5.5K | 2.3K | 2.05M | $0.30 | 3.4m |
| 14 | PASS | 76.4K | 5.20M | 20.6K | 11.5K | 5.29M | $0.88 | 9.7m |
| 15 | PASS | 24.0K | 688.0K | 4.0K | 936 | 716.0K | $0.16 | 2.9m |

### Round r4 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 41.2K | 90.9K | 1.5K | 50 | 133.6K | $0.11 | 0.6m |
| 2 | PASS | 7.9K | 105.0K | 834 | 7 | 113.7K | $0.03 | 0.3m |
| 3 | PASS | 13.7K | 126.2K | 693 | 0 | 140.6K | $0.05 | 0.3m |
| 4 | PASS | 7.0K | 156.5K | 953 | 45 | 164.5K | $0.04 | 0.4m |
| 5 | PASS | 6.0K | 180.2K | 1.3K | 127 | 187.5K | $0.04 | 0.5m |
| 6 | PASS | 10.1K | 262.5K | 1.4K | 32 | 274.0K | $0.06 | 0.5m |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — |
| 8 | PASS | 11.1K | 439.2K | 2.0K | 338 | 452.3K | $0.09 | 0.7m |
| 9 | PASS | 12.0K | 436.7K | 1.4K | 75 | 450.2K | $0.08 | 0.5m |
| 10 | PASS | 7.0K | 324.4K | 870 | 22 | 332.2K | $0.06 | 0.3m |
| 11 | PASS | 5.5K | 433.2K | 981 | 0 | 439.7K | $0.06 | 0.4m |
| 12 | PASS | 37.7K | 1.61M | 8.1K | 2.4K | 1.65M | $0.32 | 2.7m |
| 13 | PASS | 9.5K | 641.2K | 3.8K | 1.6K | 654.5K | $0.12 | 1.2m |
| 14 | PASS | 20.3K | 1.72M | 5.8K | 2.0K | 1.74M | $0.27 | 2.2m |
| 15 | PASS | 4.0K | 610.9K | 1.3K | 203 | 616.2K | $0.08 | 0.5m |

## Round r5 — per item

| Item | Verdict | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| [`cpp_duckdb_parquet_bound_schema`](../../../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | FAIL | 143.5K | 8.53M | 25.4K | 10.2K | 8.70M | $1.39 | 17.0m |
| [`cpp_duckdb_sql_export_sources`](../../../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | PASS | 226.1K | 7.91M | 28.7K | 13.7K | 8.16M | $1.53 | 19.0m |
| [`dev3_js_react_hidden_hydration_hang`](../../../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | PASS | 125.4K | 2.97M | 16.5K | 6.9K | 3.12M | $0.71 | 6.9m |
| [`js_vue_vapor_select_sync`](../../../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | FAIL | 160.3K | 6.64M | 38.5K | 18.1K | 6.84M | $1.37 | 20.8m |
| [`js_vue_vapor_transition_slots`](../../../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | FAIL | 259.5K | 11.54M | 46.5K | 20.6K | 11.85M | $2.14 | 19.7m |
| [`python_mypy_two_phase_sequential`](../../../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | PASS | 117.3K | 4.05M | 19.6K | 7.4K | 4.19M | $0.84 | 7.7m |
| [`python_polars_sql_aggregate_groups`](../../../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | FAIL | 180.4K | 10.30M | 39.7K | 14.4K | 10.52M | $1.79 | 15.8m |
| [`python_pydantic_deque_schema`](../../../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | PASS | 113.8K | 1.97M | 15.0K | 1.7K | 2.10M | $0.57 | 5.0m |
| [`rust_cargo_locked_prerelease`](../../../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | FAIL | 82.0K | 1.04M | 7.6K | 1.1K | 1.13M | $0.34 | 2.8m |
| [`rust_nushell_finally_unwind`](../../../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | PASS | 91.7K | 2.51M | 21.7K | 9.9K | 2.63M | $0.65 | 6.5m |
| [`rust_nushell_record_commands`](../../../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | PASS | 112.4K | 2.86M | 24.1K | 6.5K | 2.99M | $0.75 | 11.5m |
| [`rust_wasmtime_component_exceptions`](../../../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | PASS | 190.2K | 2.72M | 17.1K | 5.3K | 2.93M | $0.82 | 6.5m |
| [`rust_wasmtime_sync_lower_async_entry`](../../../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | PASS | 84.1K | 1.84M | 11.7K | 1.8K | 1.93M | $0.47 | 4.3m |
| [`longrun_cpp_duckdb_optimizer`](../../../cases/dev/longrun/cpp/duckdb/sequence.yaml) | 14/14 turns | 547.3K | 25.59M | 93.2K | 32.6K | 26.23M | $4.59 | 47.5m |
| [`longrun_js_eslint_rules`](../../../cases/dev/longrun/js/eslint/sequence.yaml) | 14/14 turns | 302.6K | 7.07M | 25.7K | 4.0K | 7.40M | $1.57 | 10.6m |

### Round r5 — `longrun_cpp_duckdb_optimizer` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 43.0K | 916.2K | 5.7K | 1.3K | 964.9K | $0.23 | 3.4m |
| 2 | PASS | 50.9K | 3.09M | 8.3K | 2.3K | 3.15M | $0.49 | 4.8m |
| 3 | PASS | 25.4K | 2.08M | 4.6K | 1.6K | 2.11M | $0.31 | 2.4m |
| 4 | PASS | 37.0K | 3.15M | 9.6K | 4.0K | 3.19M | $0.48 | 4.1m |
| 5 | PASS | 57.4K | 874.8K | 5.0K | 1.2K | 937.1K | $0.25 | 3.5m |
| 6 | unscored (gold applied) | — | — | — | — | — | — | — |
| 7 | PASS | 92.9K | 3.34M | 16.7K | 7.1K | 3.45M | $0.69 | 6.3m |
| 8 | PASS | 25.6K | 1.63M | 6.6K | 3.0K | 1.66M | $0.28 | 2.6m |
| 9 | PASS | 42.7K | 1.14M | 6.0K | 1.0K | 1.19M | $0.26 | 4.2m |
| 10 | PASS | 40.4K | 2.11M | 8.2K | 3.2K | 2.15M | $0.37 | 4.1m |
| 11 | PASS | 15.1K | 988.2K | 3.6K | 969 | 1.01M | $0.17 | 1.6m |
| 12 | PASS | 11.5K | 1.04M | 2.5K | 827 | 1.06M | $0.15 | 1.4m |
| 13 | PASS | 22.6K | 1.77M | 4.8K | 2.0K | 1.80M | $0.27 | 2.4m |
| 14 | PASS | 36.2K | 2.72M | 7.8K | 3.4K | 2.77M | $0.42 | 2.8m |
| 15 | PASS | 46.6K | 756.9K | 3.7K | 543 | 807.2K | $0.21 | 3.9m |

### Round r5 — `longrun_js_eslint_rules` turns

| Turn | Status | Fresh input | Cache read | Output | Reasoning | Total tokens | Cost | Agent time |
|---|---|---|---|---|---|---|---|---|
| 1 | PASS | 22.9K | 110.8K | 1.4K | 35 | 135.2K | $0.07 | 0.7m |
| 2 | PASS | 8.2K | 166.8K | 1.0K | 11 | 176.0K | $0.04 | 0.4m |
| 3 | PASS | 6.8K | 159.2K | 740 | 0 | 166.8K | $0.04 | 0.5m |
| 4 | PASS | 7.8K | 279.6K | 1.1K | 25 | 288.4K | $0.05 | 0.5m |
| 5 | PASS | 6.8K | 262.5K | 1.4K | 111 | 270.7K | $0.05 | 0.6m |
| 6 | PASS | 10.0K | 363.5K | 1.3K | 11 | 374.8K | $0.07 | 0.5m |
| 7 | unscored (gold applied) | — | — | — | — | — | — | — |
| 8 | PASS | 11.3K | 491.6K | 2.2K | 427 | 505.1K | $0.09 | 0.8m |
| 9 | PASS | 10.7K | 477.8K | 1.5K | 63 | 490.0K | $0.08 | 0.6m |
| 10 | PASS | 7.1K | 350.7K | 750 | 10 | 358.6K | $0.06 | 0.4m |
| 11 | PASS | 5.4K | 465.9K | 949 | 0 | 472.3K | $0.07 | 0.4m |
| 12 | PASS | 29.1K | 1.32M | 5.6K | 1.2K | 1.35M | $0.25 | 2.0m |
| 13 | PASS | 7.6K | 502.3K | 2.1K | 698 | 512.0K | $0.09 | 0.8m |
| 14 | PASS | 19.9K | 1.67M | 4.6K | 1.3K | 1.70M | $0.25 | 1.7m |
| 15 | PASS | 148.7K | 453.0K | 1.2K | 128 | 602.9K | $0.36 | 0.6m |

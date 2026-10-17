# GOLD frozen suite

**Frozen 2026-10-15. Codex gpt-6.1-sol baseline published 2026-10-17** (results:
[docs/GOLD.md](../GOLD.md#results)). The manifest is
[`configs/suites/gold.txt`](../../configs/suites/gold.txt): 13 one-shots and two
15-turn sequences.

## One-shots

- `oneshot/js/vue_vapor_transition_slots`
- `oneshot/js/vue_vapor_select_sync`
- `oneshot/js/react_hidden_hydration_hang`
- `oneshot/cpp/duckdb_sql_export_sources`
- `oneshot/cpp/duckdb_parquet_bound_schema`
- `oneshot/python/mypy_two_phase_sequential`
- `oneshot/python/polars_sql_aggregate_groups`
- `oneshot/python/pydantic_deque_schema`
- `oneshot/rust/wasmtime_sync_lower_async_entry`
- `oneshot/rust/wasmtime_component_exceptions`
- `oneshot/rust/nushell_record_commands`
- `oneshot/rust/nushell_finally_unwind`
- `oneshot/rust/cargo_locked_prerelease`

## Long sequences

- `longrun/cpp/duckdb` — 15 turns; turn 6 is unscored.
- `longrun/js/eslint` — 15 turns; turn 7 is unscored.

## Dropped at calibration

Light all-pass items below the heavy-work bar:
`aiohttp_paused_content_eof`,
`carbon_period_end_sync`, `symfony_jsonpath_singular`,
`dbal_sqlite_alter_preserves_constraints`, `commonmark_fence_tabs`,
`poetry_show_outdated_explicit_source`, `cpphttplib_query_verbatim`,
`redis_acl_effective_keys`, `yamlcpp_binary_emit_styles`,
`undici_async_mock_reply`, and `fastify_query_method`.

`react_hidden_hydration_hang` is light and always passed, but stays in as the
React item.

`guzzle_cookie_prefixes` was not frozen; all available samples predated its
harness repair and are void.

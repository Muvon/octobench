# GOLD

GOLD is octobench's frozen heavy-work suite for comparing AI coding clients on
the same model. Every client receives the same model and system prompt. The
reported dimensions stay separate:

- solve rate: whether the client's implementation passes objective validation;
- token efficiency: how many model tokens the client spends on the work; and
- speed: agent wall-clock time.

The suite is designed to expose differences in client navigation, tool use,
context handling, and verification on substantial repository work. It is not a
model comparison. The current suite contains 13 one-shots and two 15-turn
sequences. It was frozen on 2026-10-15.

## Results

The aggregate table is published in the GOLD section of
[BENCHMARK.md](../BENCHMARK.md); each column's per-round record, with every
item linked to its case, is under [docs/gold/results/](gold/results/).

| Column | Rounds | Per-round record |
|---|---|---|
| codex gpt-6.1-sol | 5 (2026-10-16 – 2026-10-17) | [codex-gpt-6.1-sol.md](gold/results/codex-gpt-6.1-sol.md) |

Run notes for the published column:

- One infrastructure failure was rerun inside its round: r3
  `vue_vapor_select_sync` stopped on the provider error "Selected model is at
  capacity"; the rerun replaced it. Two incomplete judge panels were rejudged.
- Long-run judge prompts listed changed file paths without the diff until
  2026-10-17, so the published judge mean covers one-shots only. The judge is
  diagnostic; solve rate and efficiency do not use it.
- From 2026-10-16 the setup of `polars_sql_aggregate_groups`,
  `duckdb_sql_export_sources`, and `duckdb_parquet_bound_schema` removes the
  upstream `AI_POLICY.md` (rules for upstream issues and pull requests), after
  one Codex run declined the task because of it. No test reads that file;
  polars was re-proven 3x afterwards.

## Selection and admission

Every item comes from real, merged, human-authored upstream work from August
to October 2026. Changes whose authors disclosed AI-generated implementation or
tests were excluded. The prompts preserve three realistic levels of detail:
acceptance specifications, issue reports, and short maintainer requests.

Only the maintainers' own upstream tests judge a solution. Those tests are
restored byte-for-byte from the gold commit and are never edited for GOLD. Each
item passed all of these gates:

1. the base source failed and the gold source passed three consecutive times
   (`VERIFY_REPEAT=3`);
2. an alignment audit traced every executed assertion to the instruction or a
   visible repository convention;
3. a core-coverage check showed that a plausible fix missing the main behavior
   still fails; and
4. validation was hardened by restoring test-runner and harness files from the
   gold commit and cleaning the relevant test directories, so agent changes
   cannot manufacture a pass.

Candidates were then calibrated on the current `gpt-6.1-sol` tier with both
Codex and Octomind. An item was retained when it was heavy (roughly 2M or more
tokens per run after pooling valid samples across clients) or consistently hard
because a client missed a stated rule. Tool-call counts were not used: the two
clients expose tools at different granularities.

Light all-pass items dropped at calibration were
`aiohttp_paused_content_eof`,
`carbon_period_end_sync`, `symfony_jsonpath_singular`,
`dbal_sqlite_alter_preserves_constraints`, `commonmark_fence_tabs`,
`poetry_show_outdated_explicit_source`, `cpphttplib_query_verbatim`,
`redis_acl_effective_keys`, `yamlcpp_binary_emit_styles`,
`undici_async_mock_reply`, and `fastify_query_method`.

`react_hidden_hydration_hang` is also light and always passed, but was kept as
the suite's React item: React is too widely used to leave out of the
JavaScript core.

## Frozen items

Calibration cells show `verdict tokens`, with tokens in millions. Multiple
entries are repeat samples. These are selection runs, not baseline results.
The final check is one Codex `gpt-6.1-sol` run of every item under the frozen
instructions, harness and image (`octobench-agent:gold7`) on 2026-10-16.

| Item | Language | Upstream PR | Prompt style | Codex calibration | Octomind calibration | Codex final check |
|---|---|---|---|---|---|---|
| [`vue_vapor_transition_slots`](../cases/dev/oneshot/js/vue_vapor_transition_slots/case.yaml) | JavaScript | [vuejs/core#15758](https://github.com/vuejs/core/pull/15758) | issue report | FAIL 9.59M | FAIL 10.12M | FAIL 11.85M |
| [`vue_vapor_select_sync`](../cases/dev/oneshot/js/vue_vapor_select_sync/case.yaml) | JavaScript | [vuejs/core#15827](https://github.com/vuejs/core/pull/15827) | acceptance spec | FAIL 5.86M | FAIL 6.15M | FAIL 7.83M |
| [`react_hidden_hydration_hang`](../cases/dev/oneshot/js/react_hidden_hydration_hang/case.yaml) | JavaScript | [facebook/react#37135](https://github.com/facebook/react/pull/37135) | short maintainer request | PASS 0.78M; PASS 3.22M | PASS 1.46M; PASS 0.99M | PASS 2.22M |
| [`duckdb_sql_export_sources`](../cases/dev/oneshot/cpp/duckdb_sql_export_sources/case.yaml) | C++ | [duckdb/duckdb#26843](https://github.com/duckdb/duckdb/pull/26843) | acceptance spec | FAIL 9.94M | TIMEOUT 3.82M | PASS 8.90M |
| [`duckdb_parquet_bound_schema`](../cases/dev/oneshot/cpp/duckdb_parquet_bound_schema/case.yaml) | C++ | [duckdb/duckdb#26827](https://github.com/duckdb/duckdb/pull/26827) | acceptance spec | PASS 8.84M | FAIL 4.15M | FAIL 9.39M |
| [`mypy_two_phase_sequential`](../cases/dev/oneshot/python/mypy_two_phase_sequential/case.yaml) | Python | [python/mypy#21973](https://github.com/python/mypy/pull/21973) | issue report | PASS 3.77M | FAIL 2.23M | PASS 2.43M |
| [`polars_sql_aggregate_groups`](../cases/dev/oneshot/python/polars_sql_aggregate_groups/case.yaml) | Python | [pola-rs/polars#29754](https://github.com/pola-rs/polars/pull/29754) | acceptance spec | FAIL 6.12M | FAIL 4.83M | FAIL 8.57M |
| [`pydantic_deque_schema`](../cases/dev/oneshot/python/pydantic_deque_schema/case.yaml) | Python | [pydantic/pydantic#13757](https://github.com/pydantic/pydantic/pull/13757) | acceptance spec | PASS 2.10M; PASS 1.68M | PASS 1.84M | PASS 3.21M |
| [`wasmtime_sync_lower_async_entry`](../cases/dev/oneshot/rust/wasmtime_sync_lower_async_entry/case.yaml) | Rust | [bytecodealliance/wasmtime#14574](https://github.com/bytecodealliance/wasmtime/pull/14574) | issue report | PASS 3.59M | PASS 3.11M | PASS 3.83M |
| [`wasmtime_component_exceptions`](../cases/dev/oneshot/rust/wasmtime_component_exceptions/case.yaml) | Rust | [bytecodealliance/wasmtime#14549](https://github.com/bytecodealliance/wasmtime/pull/14549) | short maintainer request | PASS 2.12M | PASS 2.91M | PASS 1.69M |
| [`nushell_record_commands`](../cases/dev/oneshot/rust/nushell_record_commands/case.yaml) | Rust | [nushell/nushell#19190](https://github.com/nushell/nushell/pull/19190) | acceptance spec | FAIL 3.40M | PASS 2.03M | PASS 2.33M |
| [`nushell_finally_unwind`](../cases/dev/oneshot/rust/nushell_finally_unwind/case.yaml) | Rust | [nushell/nushell#19052](https://github.com/nushell/nushell/pull/19052) | short maintainer request | PASS 2.59M; PASS 2.63M | PASS 2.22M | PASS 2.50M |
| [`cargo_locked_prerelease`](../cases/dev/oneshot/rust/cargo_locked_prerelease/case.yaml) | Rust | [rust-lang/cargo#17464](https://github.com/rust-lang/cargo/pull/17464) | issue report | FAIL 1.35M | FAIL 1.24M | FAIL 1.06M |
| [`duckdb`](../cases/dev/longrun/cpp/duckdb/sequence.yaml), 15 turns | C++ | duckdb/duckdb #24258, #24228, #24526, #24683, #24700, #24015, #24600, #24760, #24788, #24784, #24669, #24786, #24660, #24901, #24846 | mixed issue reports and requests | not calibrated | not calibrated | 14/14 turns PASS 25.2M |
| [`eslint`](../cases/dev/longrun/js/eslint/sequence.yaml), 15 turns | JavaScript | eslint/eslint #21047, #21050, #21051, #21057, #21058, #21069, #21094, #21096, #21081, #21167, #21166, #21163, #21173, #21175, #21207 | mixed issue reports and requests | not calibrated | not calibrated | 14/14 turns PASS 7.6M |

The Octomind `duckdb_sql_export_sources` calibration sample hit the former
45-minute case limit; every one-shot now has a 90-minute limit.

In the final check every Codex one-shot failure was traced to a requirement the
instruction states (Cargo C4; Polars P1, P2, P4 and P6; DuckDB Parquet D6; Vue
select S2; Vue transition hydration with `appear`), so no instruction was
changed. `duckdb_sql_export_sources` passed under its repaired instruction, and
both sequences ran end to end with their unscored turns and the repaired ESLint
turn 12. The tool audit found no forbidden tool use.

Void observations are excluded above: Octomind failures at 2.28M for
`nushell_finally_unwind`, 0.71M for `aiohttp_paused_content_eof`, and 2.05M for
`cargo_locked_prerelease`; the Codex `cargo_locked_prerelease` infrastructure
failure; and the Octomind 2.40M `pydantic_deque_schema` run whose tokens were
valid but whose verdict was invalidated by a deselection-path harness bug. All
pre-repair `guzzle_cookie_prefixes` samples are also void.

## Unscored sequence turns

An unscored turn is not sent to the client and contributes no solve, token, or
time result. Its gold source change is applied so later turns still begin from
the intended cumulative repository state.

- DuckDB turn 6 is unscored because no admissible upstream test asserts the
  row-group pruning behavior at the core of the task; the selected generic
  tests pass without the simplification.
- ESLint turn 7 is unscored because its upstream tests cover the
  override/implements exemptions, not computed literal keys under name-based
  ignores; a fix missing the requested core behavior can pass them.

The frozen manifest is [configs/suites/gold.txt](../configs/suites/gold.txt).
Run and publication mechanics remain governed by
[the GOLD protocol](gold/PROTOCOL.md) and [HARNESS.md](HARNESS.md).

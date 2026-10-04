# octobench GOLD v2 — 15 one-shots and 5 long-run sequences

## Purpose

GOLD shows, per model × client pair, **solve rate** and **efficiency** (cost,
tokens, wall time), on the smallest task set whose results are enough to say
"this pair is better or cheaper than that one", at the lowest run cost that
still supports the conclusion:

- **One-shot tasks** cover a variety of task types (bug fix, feature,
  performance, symptom-driven debugging, refactor) and complexity tiers across
  the five languages, each simple enough that its score reads plainly.
- **Long-run sequences** test one persistent session over many turns,
  including sessions that outgrow the model's context window, so context
  management (compaction, recovery after it) is part of the result.
- Every item earns its slot: either verdicts split across columns (solve
  signal) or every column solves it and it compares cost on equal work. Items
  every column passes without efficiency value, or every column fails, are cut.
- A failure counts only after it is classified a legitimate model failure, not
  a case defect, infra or flake. Each item runs three times; results are
  reported as means, and a difference inside the run-to-run spread is a tie.

## Suite and regeneration commands

[configs/suites/gold.txt](../configs/suites/gold.txt) contains 20 entries:
15 one-shots (three per language) and five long-run sequences. A `:N` suffix
means turns 1 through N in the same persistent session. V2 runs DuckDB through
13, Cargo through 7, CPython through 11, all 15 ESLint turns, and all six
PhpSpreadsheet turns: 52 long-run turns and 67 scored tasks in total.

`scripts/bench.sh <oneshot|longrun> ... --suite gold` selects the matching mode.
The launcher support for turn caps is being added separately. Regenerate the
GOLD-SUMMARY, GOLD-RESULTS, and GOLD-LONGRUN-RESULTS blocks in
[BENCHMARK.md](../BENCHMARK.md) from explicit v2 run
inputs, using the existing command forms:

```bash
scripts/update_benchmark.py --suite=gold --markers=GOLD 'label=results-gold-v2-oneshot-*/*/results.json' ...
scripts/longrun_table.py    --suite=gold --markers=GOLD 'label=results-gold-v2-longrun-*/*/results.json' ...
```

Replace `label` and the trailing arguments with each column's result patterns.
Before regeneration, the long-run reporting tools must support `:N` and
aggregate only the selected turns. That tooling work is separate from this
content revision; the former `gold_scorecard.py` is being removed separately.
Do not mix pre-repair and v2 runs or publish full-sequence totals as
capped-sequence results.

## V2 one-shot selection

Grounding uses the current GOLD-RESULTS block (updated 2026-09-11), supplemented
by the main one-shot table for the three newly admitted items and the supplied
106-cell audit. These are historical observations, not three-round v2 means.
`tok` below excludes cache reads; time is agent runtime, excluding setup,
validation, and judging. Short column names retain both model and client:
Claude = Opus 5/Claude; Sol and Luna = GPT-5.6; GLM and Flash = GLM-5.3 and
GLM-5.3-Flash; OM = Octomind, OC = OpenCode.

| Case | Axis | Grounding |
|---|---|---|
| `cpp/yamlcpp_binary_emit_styles` | Solve; same-model client split | 5/8 pass. Luna-Codex, GLM-OC, and Flash-OC add an extra blank line after empty Literal; their OM counterparts pass. GLM j=47.33 vs 93.67. |
| `cpp/yamlcpp_octal_scalars` | Solve; parser edge | 3/8 pass: Sol-Codex and both GLM clients. Five legitimate failures accept invalid `0oxff`; Claude j=38.33, Sol j=89.33. |
| `cpp/redis_acl_effective_keys` | Tokens, cost, speed | 8/8 pass; 87K–319K tok, $0.07–$4.12, 3–74m. GLM-OC takes 319K/74m versus GLM-OM 180K/23m. |
| `js/gemini_cancelled_turn_rollback` | Solve; cancellation state | Claude and Sol-Codex pass; Luna-Codex fails, leaving history length 3 instead of 0. j=92.67/90.33/38.33 respectively; only these three columns have results. |
| `js/fastify_query_method` | Speed, interaction cost | 8/8 pass; 3–24m and 89K–203K tok. Sol-Codex takes 19 steps/5m; GLM-OC 103 steps/24m; Luna-OM 122 steps/5m. |
| `js/undici_async_mock_reply` | Tokens, speed | 8/8 pass; 66K–196K tok and 4–28m. Sol-Codex 66K/5m versus Luna-OM 196K/5m and Flash-OM 153K/28m. |
| `php/commonmark_fence_tabs` | Solve; tab parsing | 6/8 pass. Luna fails on both clients: Codex loses the first info-string character; OM preserves a tab where three spaces are required. Sol-Codex now passes, j=91.67. |
| `php/guzzle_cookie_prefixes` | Solve; normalization | 5/8 pass. Sol-Codex, Luna-Codex, and Luna-OM reject valid normalized host-only/root cookies; Claude and all four GLM/Flash columns pass. |
| `php/carbon_period_end_sync` | Tokens, cost, speed | 8/8 pass; 56K–238K tok, $0.03–$4.37, 2–36m. GLM-OM is 238K/36m; Luna-OM 56K/2m. |
| `python/aiohttp_paused_content_eof` | Solve; bounded buffering | Claude and Sol-Codex pass; Luna-Codex expands all 5 MiB instead of retaining at most 2 MiB. j=92.0/92.0/40.67; only these three columns have results. |
| `python/scrapy_http2_frame_size` | Solve; protocol configuration | Claude and Luna-Codex pass; Sol-Codex rejects a 65,535-byte frame despite a 1 MiB configured limit. j=92.67/92.0/37.33; only these three columns have results. |
| `python/pydantic_pipeline_constraints` | Tokens, speed | 8/8 pass; 31K–110K tok, 1–15m. Luna-OM takes 31K/1m; Flash-OC 110K/15m. |
| `rust/tokio_alt_timer_cancel_race` | Speed; concurrency anchor | Current data is 8/8 pass, 54K–141K tok and 2–28m. GLM-OC now completes in 8m; the old 45m runaway is not the current selection rationale. |
| `rust/ripgrep_maxdepth_ignore_skip` | Tokens, speed | 8/8 pass; 62K–152K tok, 3–22m. Sol-Codex takes 62K/4m; GLM-OC 152K/16m. |
| `rust/chrono_iter_reverse` | Tokens, speed | 8/8 pass; 51K–237K tok, 4–24m. GLM-OM takes 237K/23m; Claude 51K/4m. |

## V2 long-run selection

The GOLD-LONGRUN-RESULTS block (updated 2026-09-19) records the original full
sequences. The prefix counts below are recomputed from the supplied historical
per-turn results; they include defects and undetermined failures and are not
valid v2 solve rates. Efficiency ranges are explicitly labeled as full-sequence
historical totals, with tokens including cache reads. Removed tails passed in
every recorded column and add cost beyond the retained failure and context
coverage.

| Sequence retained | Axis | Grounding |
|---|---|---|
| `cpp/duckdb:13` | Solve, context, efficiency | Historical prefix: Sol 13/13; Claude, Luna-Codex, GLM-OM 11/13; Luna-OM 9/13; Flash-OM 12/13. Both OC columns lack data. Legitimate splits at 6, 7, 9, 13; Luna-OM #9 remains undetermined after failed dependency restoration. Full 15-turn totals: 55.8M–211.9M tokens, $1.97–$121.78, 77–501m. |
| `rust/cargo:7` | Solve, context, diagnostics | Historical prefix: 4/7–6/7; full sequence 7/10–9/10. Turn 1 has six legitimate sidecar failures and #4 one legitimate feature-gating failure. #2/#6/#7 instructions were repaired (see below), so their historical results are not comparable. Full 10-turn totals: 39.5M–192.6M tokens, $1.15–$111.85, 46–254m. |
| `python/cpython:11` | Cancellation, exception handling, context | Historical prefix: Flash-OC 5/11, Flash-OM 8/11, other six columns 7/11; full sequence 8/14–11/14. #2/#5/#10 instructions were repaired (see below); unresolved #4/#7/#11 cells need the now-verbose logs. Full 14-turn totals: 22.0M–81.4M tokens, $0.62–$28.58, 30–231m. |
| `js/eslint` (15) | Solve, context, autofix safety | Historical 12/15–14/15. Legitimate failures at #5, #13, #15; #12 was a descriptor-detection case defect (instruction repaired; historical #12 results are not comparable), with one provider timeout. Full totals: 13.6M–60.5M tokens, $0.47–$20.98, 24–156m. |
| `php/phpspreadsheet` (6) | Solve; short-session comparison | Sol-Codex 5/6, Luna-Codex 4/6, other six columns 6/6. Legitimate reader-class failure at #2 and overlapping-column deletion failures at #6. Totals: 4.3M–18.9M tokens, $0.26–$11.72, 13–88m. |

## Context window

Every client works inside an emulated 200K-token window, set by
`OCTOBENCH_CONTEXT_WINDOW=200000`. The campaign configuration is:

| Client | Window and compaction configuration |
|---|---|
| Claude 2.1.221 | `CLAUDE_CODE_AUTO_COMPACT_WINDOW=200000` in the environment. |
| Codex 0.146.0 | `model_context_window=200000`; compacts at 90% of that window. |
| OpenCode v1.18.34 | Each model's `limit.context` is 200000. Without this explicit limit, OpenCode cannot learn it on the sealed network and never compacted. |
| Octomind | Configured for compression at 70K tokens and a session ceiling of `max_session_tokens_threshold=200000`. |

The supplied `cross200k.txt` records the first turn where accumulated session
content passes 200K. These measurements locate context pressure; they do not
by themselves prove when a client compacted, and they are not cumulative billed
tokens including repeated cache reads.

| Retained sequence | Claude | GLM-OpenCode | Flash-OpenCode | Observed first crossing |
|---|---|---|---|---|
| DuckDB | 2 | No measurement | No measurement | 2 |
| Cargo | 1 | 2 | 2 | 1–2 |
| CPython | 7 | 8 | 8 | 7–8 |
| ESLint | 12 | 10 | 13 | 10–13 |
| PhpSpreadsheet | Never (196K at turn 6) | Never (118K) | Never (107K) | Never; the short-session item |

The supplied crossing report does not measure Codex or Octomind crossings.
Codex compaction becomes observable only with the session-log retention being
added separately. Compression thresholds differ even with the common ceiling;
record the configuration and actual compaction events with each v2 round.

## Audit and instruction repairs

The supplied audit examined **106 failing cells: 53 legitimate model failures,
40 case defects, 4 infrastructure failures, and 9 undetermined**. These counts
cover the audited candidate set, including exclusions, rather than just v2.
No flake or cascade was confirmed solely from timing or failed restoration.

ESLint #12 and CPython #10 are case defects, not valid-hard turns. This corrects
the 2026-08-31 audit: ESLint #12 was labeled valid-hard despite asking for
return-path analysis while its selected change requires descriptor detection.
CPython #10 asked for GeneratorExit handling while its selected assertion
concerns KeyboardInterrupt and a suppressed sibling exception. The older
CPython #10 cascade diagnosis is also insufficient:
the audited Flash-OpenCode run successfully restored #7 before failing #10.
CPython #5's earlier valid-hard label is superseded by its undeclared internal
member requirement. A passing column proves solvability, not derivability.

This revision repairs the following contracts without changing gold SHAs,
protected test paths, dependencies, or selected assertions:

| Turn | Instruction repair |
|---|---|
| CPython #2 | Cancellation already observed at readiness leaves the connection pending; the cancelled call raises without a loop error, and the next accept returns the same usable peer connection. |
| CPython #5 | Retain output through cancellation and process waiting; explicitly expose incrementally populated `_stdout_buf`, propagate cancellation, finish retries after child termination, close stdin, and never replay supplied input. |
| CPython #10 | Propagate KeyboardInterrupt/SystemExit and report each suppressed sibling exception exactly once through the loop handler's `exception` context, preserving earlier generator-close behavior. |
| ESLint #12 | Detect only correctly positioned descriptors of enabled, unshadowed Object/Reflect built-ins; cover optional chaining, maps versus computed keys, and the directly bound `isPropertyDescriptor` utility contract shared by the three accessor rules. |
| Cargo #2 | Pin the redundant-homepage headline naming `package.repository`; preserve snippets, help, notes, cached replay, warning suppression, and denial status. |
| Cargo #6 | Calculate and retain ADDING publication-age annotations relative to `--publish-time`, alongside the historical LOCKING headline and unchanged lockfile conventions. |
| Cargo #7 | Specify literal LOCKING age/timestamp suffixes, including `as of 7 days ago`, while preserving selection, lockfiles, and available-version details. |

Tags are adjusted to the repaired contracts: CPython #2 and Cargo #7 are medium;
CPython #5/#10, ESLint #12, and Cargo #2/#6 are complex. CPython #2, ESLint #12,
and Cargo #2 use acceptance-spec style; ESLint #12 and Cargo #2 become full-spec.
The other existing full-spec and follow-up tags remain appropriate.
All 14 CPython test commands append `-v`; selectors and pass/fail semantics stay
identical. Internal names are stated only where selected assertions bind to
them. The CPython #5 error attribution is source-traced; old logs do not contain
the AttributeError traceback.

All seven requested defect findings were supported by the selected gold tests
and fixes. This is a content preparation revision: it does not claim new
fail-at-base/pass-with-gold proof or client reruns. Before publishing v2 results,
repeat the proof and requested client/model runs under [HARNESS.md](HARNESS.md),
keeping pre-repair observations separate.

## Exclusions and reasons

| Excluded item | Reason |
|---|---|
| Long-run `cli11`, `mypy`, `doctrine_orm` | Every recorded column passes every turn: 8/8, 5/5, and 6/6 respectively. Kept sequences already cover efficiency and context depth. |
| Long-run `fastify` | Its only split is turn 4, a case defect: validation demands cache population under the normalized Content-Type beyond the instructed reuse behavior. |
| Long-run `ruff` | Its turn-4 split is infrastructure: the fixture was restored without its paired snapshot. Turn 6 fails every column; seven are legitimate annotation misses and one is an extra diagnostic-label requirement. It provides no clean ranking split. |
| One-shot `libgit2_revwalk_pathspec_root`, `webpack_lazy_backend_shutdown`, `vite_hmr_restart_stale`, `monolog_max_trace_length`, `poetry_show_outdated_explicit_source`, `click_powershell_completion`, `anyio_tls_idna2008`, `uuid_parse_panic` | Every current column passes; their efficiency coverage is supplied by the kept anchors. Historical monolog verdict splits no longer hold. |
| `prettier_setext_blockquote_marker` | Fixture/snapshot infrastructure contamination; restore them together before admission. |
| `cpphttplib_connection_upgrade_token` | Protected assertions bind unnamed internal helpers; repair the contract or validate public handshake behavior before admission. |
| `llvm_slp_root_phi_order` | Mixed: Luna retains the crash; Sol fails an exact shuffle-shape constraint. Repair validation and establish semantic correctness before admission. |
| `symfony_console_wrap` | Mixed: Claude leaves an overwide line; Luna is penalized for ANSI escape bytes counted as visible width. Repair validation before admission. |

## Methodology

Run **three full rounds per model × client column** on the complete v2 suite,
with the same versions, sealed environment, context configuration, and selected
turn caps. Keep all three observations and report means with min–max for cost,
tokens, and time. A gap inside the run-to-run spread is a tie; one historical
run or a mean judge score is not three independent task attempts.

Report objective solve rate separately from cost, tokens, and time. Classify
failed cells before interpreting them: case defects, infrastructure, leakage,
nondeterminism, and undetermined outcomes are not legitimate model failures.
Report missing or excluded observations and the scoring denominator explicitly.
Compare efficiency only on items every compared column solved, using the same
item set across those columns. Keep unsuccessful-run expenditure visible
separately so cheaper failure is not confused with cheaper completion.

Report non-cache tokens and cache reads separately, with a clearly labeled total;
the historical one-shot and long-run tables use different token totals. Agent
wall time excludes setup, validation, and judging. Compare like-for-like client
versions and model pairings, and distinguish a model comparison from a
same-model client comparison. Preserve raw validation and session evidence,
including dependency restoration outcomes and compaction events.

## Remaining evidence gaps

- Gemini rollback, aiohttp EOF, and Scrapy frame-size results exist only for
  Claude, Sol-Codex, and Luna-Codex. The other five columns need full v2 rounds.
- CPython #4 has five undetermined cells, #7 one, and #11 two until verbose logs
  identify the failing assertions. Three other #4 failures are already
  legitimate; adding `-v` does not retroactively classify the missing evidence.
- DuckDB #9 on Luna-OM is the ninth undetermined cell: prerequisite #7 failed
  restoration. A missing CROSS_PRODUCT does not establish cascade causation;
  inspect the exact tree or rerun after successful restoration.
- Codex compaction requires the separately added session-log retention. The
  crossing report also has no Codex/Octomind measurements, and DuckDB lacks both
  OpenCode result columns.
- The excluded Ruff #6 diagnostic-label discrepancy needs its exact historical
  validation blob; LLVM's different shuffle shape still needs behavioral proof.
- Repaired instructions need fresh proof and client runs. Turn-cap support in
  the launcher and reporting tools must be complete before v2 regeneration.

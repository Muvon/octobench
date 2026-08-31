# octobench GOLD — hand-picked 30 (initial version, 2026-08-31)

One suite: `configs/suites/gold.txt` — 30 lines, `oneshot/<lang>/<case>` ×20 +
`longrun/<lang>/<repo>` ×10; `scripts/bench.sh <oneshot|longrun> ... --suite gold`
selects the lines matching the mode. Table blocks live at the top of
BENCHMARK.md (GOLD-SUMMARY / GOLD-RESULTS / GOLD-LONGRUN-RESULTS markers):

```
scripts/update_benchmark.py --suite=gold --markers=GOLD 'label=results-gold-oneshot-*/*/results.json' ...
scripts/longrun_table.py    --suite=gold --markers=GOLD 'label=results-gold-longrun-*/*/results.json' ...
scripts/gold_scorecard.py   --suite=gold 'label=results-gold-oneshot-*/*/results.json results-gold-longrun-*/*/results.json' ...
```

The scorecard is the combined-efficiency view (one column per client over ALL
30 gold items — oneshot cases + longrun turns together): solve rate, judge
mean, $/solve, cost- and token-waste %, median/p90/max time, cache-read,
steps-per-item from the recorded traces (all four provider formats, including
claude's `_stream_*.jsonl`).

Picked from the full 2026-08 result set (BENCHMARK.md matrix:
glm-5.3-opencode, gpt-5.6-sol-codex, glm-5.3-octomind, claude-opus-5-claude,
gpt-5.6-luna-codex; longrun 6 columns) so that the set, taken together, ranks a
client on **three axes at once**:

- **SOLVING** — cases whose verdict *splits* across clients/models. A case
  everyone passes or everyone fails ranks nobody.
- **TOKEN EFFICIENCY** — cases everyone solves but with a ≥3x non-cache token
  spread: same outcome, very different context discipline.
- **SPEED** — same cases read on wall time and step count; plus one explicit
  runaway-containment probe.

Every pick is grounded in recorded numbers below (j = judge mean, tok =
non-cache tokens). Excluded-case reasons are at the end — an all-fail case is
either broken or ranks nobody, so none are in GOLD.

## Oneshot 20 (4 per language, all from the proven oneshot-50 with 5-client data)

### cpp
| case | axis | grounding |
|---|---|---|
| `yamlcpp_binary_emit_styles` | SOLVING (harness) | Same model, opposite verdicts: glm-opencode FAIL j=32.5 vs glm-octomind PASS j=95.67. Also killed both archived deepseek columns (49.33/36.33). |
| `yamlcpp_octal_scalars` | SOLVING (edge) | luna FAIL j=39.33, everyone else PASS 89–94. The pass octomind earned came from its verify-gate (instrumented 2026-08-12) — harness mechanics visible in the verdict. |
| `redis_acl_effective_keys` | TOKENS+SPEED | All pass; 68K tok/3m (sol) ↔ 357K tok/35m (octomind) ↔ 41m (opencode). Big-codebase exploration discipline. |
| `libgit2_revwalk_pathspec_root` | TOKENS | All pass; 76K/3m (sol) ↔ 441K/26m (octomind), cost $0.98 ↔ $3.07. Widest pure token spread in cpp. |

### js
(the 50 has no *valid* verdict-splitting js case — pinopretty/react fail everyone — so js carries the efficiency axes)
| case | axis | grounding |
|---|---|---|
| `fastify_query_method` | SPEED (steps) | All pass; 20 steps/4m (sol) ↔ 203 steps/31m (octomind), 124 steps (opencode). Step economy under a real framework repo. |
| `webpack_lazy_backend_shutdown` | SOLVING-quality | All pass but j splits: octomind 87.33 vs 92.33–94.0 elsewhere; tok 55K ↔ 120K. |
| `vite_hmr_restart_stale` | TOKENS | All pass; 33K/2m (sol) ↔ 252K/19m (octomind), j 88.33–93.0. |
| `undici_async_mock_reply` | TOKENS+SPEED | All pass; 79–96K/4–5m (claude/sol) ↔ 267K/14m (octomind). Consistent mid-weight spread. |

### php
| case | axis | grounding |
|---|---|---|
| `commonmark_fence_tabs` | SOLVING (model ceiling) | Only claude passes (j=93.67, validate 5/5 OK — proves the case solvable). glm, gpt-sol, gpt-luna, both deepseeks all FAIL j 38–46. Separates the top model from everything else. |
| `guzzle_cookie_prefixes` | SOLVING (model family) | gpt family fails (sol 41.33, luna 42.33), glm+claude pass 94–95. Clean model-axis split with harness held constant (codex fails on both its models). |
| `monolog_max_trace_length` | SOLVING (harness, replicated) | The purest harness discriminator: opencode FAIL / octomind PASS **on two model families** (glm: 39.67 vs 89.33; archived deepseek: 36.0 vs 94.67). |
| `carbon_period_end_sync` | TOKENS+quality | All pass; 77K/4m (sol) ↔ 465K/37m (octomind); j 81.67 (luna) ↔ 94.0. |

### python
(the python tier of the 50 is light; this is the heaviest available — see Gaps)
| case | axis | grounding |
|---|---|---|
| `poetry_show_outdated_explicit_source` | TOKENS+SPEED | All pass; 48K/2m (sol) ↔ 157K/15m (octomind), 112K/21m (opencode). Heaviest python case. |
| `pydantic_pipeline_constraints` | TOKENS | All pass; 36K/2m (sol) ↔ 230K/15m (octomind). 6x spread. |
| `click_powershell_completion` | SOLVING-derivability | The audited "derivable from conventions" case (case-validity reference). All pass, but 3m (sol/claude) ↔ 20m (opencode). |
| `anyio_tls_idna2008` | TOKENS (mild) | All pass; 47K (claude) ↔ 121K (octomind); j 89.67–94.67. Weakest slot — placeholder until the 80-corpus python splitters get full coverage. |

### rust
| case | axis | grounding |
|---|---|---|
| `tokio_alt_timer_cancel_race` | SPEED (runaway) | The explicit containment probe: opencode INFRA — hit the 45m cap on an idle box — while every other client finishes in 2–7m. Case wording was validity-hardened (bool-return contract), so the runaway is real behaviour. |
| `chrono_iter_reverse` | TOKENS | All pass; 53K/3m (sol) ↔ 316K/29m (octomind). 6x. |
| `uuid_parse_panic` | quality+TOKENS | All pass but claude j=80.0 is the outlier vs 90.67–95.33; 40K (sol) ↔ 261K (octomind), 172K (opencode). |
| `ripgrep_maxdepth_ignore_skip` | TOKENS+SPEED | All pass; 66K/2m (sol) ↔ 242K/17m (octomind); also the `test_paths: []` convention exemplar. |

## Longrun 10 (2 per language)

| sequence | axis | grounding |
|---|---|---|
| `cpp/duckdb` (15) | ALL THREE | The crown: solving spread claude 15/15 · sol 14/15 · luna 13/15; tokens 52.7M (sol) ↔ 264.9M (claude); cost $2.33 (luna) ↔ $151.70 (claude); wall 60m ↔ 520m. No turn fails everyone (claude's 15/15 proves each turn solvable). |
| `cpp/cli11` (8) | TOKENS+SPEED | Everyone 8/8 → pure efficiency: 8.2M tok/18m (sol) ↔ 33.6M/45m (luna) ↔ 77m (octomind); cost $0.81 ↔ $17.91. |
| `js/eslint` (15) | TOKENS at depth | All recorded clients 14/15 (the shared miss is turn 12 — audit-flagged); 17.1M/23m (sol) ↔ 33.6M/42m (opencode). Deepest valid js sequence. |
| `js/fastify` (5) | SOLVING | Turn 2 (ContentType cache) splits: luna 4/5 + opencode 4/5 vs 5/5 elsewhere; Σ 332.8 ↔ 400.1. |
| `php/doctrine_orm` (6) | SOLVING | Widest clean verdict spread in longrun: sol 4/6 · luna 4/6 · octomind 5/6 · opencode 6/6 · claude 6/6, and no turn fails everyone. |
| `php/phpspreadsheet` (6) | SOLVING+SPEED | octomind 5/6 + luna 5/6 vs 6/6; wall 14m (sol) ↔ 102m (octomind). |
| `python/cpython` (14) | SOLVING at depth | Biggest solving spread of any sequence: luna 8/14 · opencode 10/14 · sol 11/14 · claude 12/14 (turns 5+10 fail all recorded clients — audit-flagged; the other 12 turns still rank everyone). |
| `python/mypy` (5) | TOKENS (same-model) | Everyone 5/5; same model, 6x apart: glm-octomind 2.9M/$1.24 vs glm-opencode 18.2M/$5.77; codex 12m vs both glm columns ~1h. |
| `rust/cargo` (10) | SOLVING+TOKENS | sol 8/10 · claude 7/10 · opencode 7/10 · luna 6/10; tokens 29.2M (sol) ↔ 244.3M (claude), 160.1M (opencode); $18.77 ↔ $138.64. Turns 1/9/10 fail all recorded clients and turn 9 depends on turn 1's feature — audit before treating those three as signal. |
| `rust/ruff` (6) | SOLVING (model flip) | The only model-axis flip in longrun: turn 6 (ClassVar/Final in NamedTuple) defeats claude, sol AND luna, while glm-opencode passes 6/6. Tokens 17.5M (luna) ↔ 77.8M (opencode). |

## Excluded, with reasons

- `rust/rustls_misplaced_extensions` — **broken case, confirmed**: compile-class
  failures (E0063 missing gold-named struct field, E0631 visibility signature);
  also the one case with no fail-to-pass proof. Fix or drop.
- `js/react_hidden_hydration_hang` — valid but fails all 7 runs; ranks nobody,
  only measures runaway containment (221m/2.8M tok octomind, $69 claude). Keep
  as an optional stress annex, outside scoring.
- `js/pinopretty_strip_controls`, `js/nest_sse_abort_signal` — fail everyone,
  assert-class; validity unconfirmed (over-specified expectations suspected) —
  audit before any use.
- `js/node_webcrypto_supports_constraints` — valid-hard (Node core, 9 files) but
  fails all recorded clients → no discrimination yet; promote once something passes it.
- Longrun `js/axios` (turns 3+4 fail all 5), `php/guzzle` (turn 4 fails all 5
  while the same change passes as a oneshot case), `rust/gitoxide` (turn 2 fails
  all 5), `php/laravel` (6 of 12 turns fail everyone) — common-fail turns =
  suspected broken turns; audit before scoring.
- Longrun `cpp/simdjson` — codex columns tainted (web_search seal bypass).
- Everything with near-uniform passes (nest, vue, symfony, aiohttp, pytest,
  pydantic, clap, tokio, ada, fmt) — anchors, not discriminators.

## Finalization checks (2026-08-31)

- All 30 suite entries exist on disk; all 20 oneshot manifests carry
  `verified: true` (fail-to-pass proven via scripts/verify_case.sh).
- Longrun legitimacy is proven empirically from the recorded campaigns: every
  turn of all 10 sequences has ≥1 client PASS (solvable — validation only exits
  0 when the held-out gold tests pass), and every sequence contains turns some
  client failed (non-trivial — the tests don't pass for free). duckdb
  additionally carries an explicit `verified: true` (15/15 cumulative proof).
- Tag balance of the oneshot 20: difficulty 1 simple / 7 medium / 9 complex /
  3 expert; task type 14 bug-fix / 5 feature / 1 performance; prompt source
  10 reverse-spec / 7 human-reconstructed / 2 original-issue / 1 composite;
  visibility 14 hidden / 6 mixed — variety per HARNESS.md §5–6, no one-shape skew.
- Validity audit of all-client-fail turns (2026-08-31, evidence-cited):
  - eslint#12 VALID-HARD, cpython#5 VALID-HARD — stay as genuine hard turns.
  - **cpython#10 BROKEN (cascade)**: declares `depends_on: [7]` but the runner
    never injects a failed predecessor's gold source, so it scores an
    independent failure that is actually turn 7's cascade. Repair: re-base its
    validation on turn 7's gold, or score it as cascade, not failure.
  - **cargo#9 BROKEN (same cascade shape, depends_on: [1])**; cargo#1 and #10
    UNCERTAIN (instructions look complete; exact failing assertions not in the
    synced tree). Same repair options.
  - Systemic finding: `depends_on` turns are mis-scored whenever a predecessor
    failed — cumulative fail-to-pass proof (verify_longrun.sh applies each gold
    fix) cannot establish a dependent turn's validity after an agent failure.
    Also hit: laravel#2/#11 (not in GOLD).
  - Confirmed BROKEN outside GOLD (stay excluded): guzzle-longrun#4
    (instruction omits the `Path=` requirements its tests check — the passing
    oneshot twin states them), gitoxide#2 (test demands legacy message casing
    contradicting the instructed message), axios#3 (hidden tests bind to
    gold-internal `internals.handlerEntries.size` + unstated semantics);
    axios#4/#5 audited VALID-HARD.
  - All four all-fail oneshot hard-tier cases (pinopretty, react, nest_sse,
    node_webcrypto) audited VALID-HARD — the hard tier is honest; they stay
    out of GOLD only because a case nobody passes ranks nobody.

## Defect repairs (2026-08-31)

Instruction-level repairs (tests and golds untouched — fail-to-pass proofs
remain valid; instruction text is not part of the proof):

- guzzle-longrun#4: added the `__Host-` `Path=` requirements from the passing
  oneshot twin (raw header must contain `Path=`; bare `Path` token invalid).
- gitoxide#2: instruction now states BOTH hard failures — missing first email
  (`Line {n} does not contain an email`) and a lone email with nothing to map
  (`{n}: Emails without a name or email to map to are invalid`, gold
  parse.rs's second error arm, which the held-out test pins via `"1:"`).
- axios#3: instruction now states the full contract the tests check — stable
  never-reused IDs, replacement/clear invalidation, mutation-safe iteration,
  and the Symbol-keyed internals object with the `handlerEntries` Map
  (spec_level behavioral→full-spec, difficulty medium→complex).
- cargo#1: instruction now states the `<artifact>.trim-paths.jsonl` naming,
  both-copies emission (original + uplifted + artifact-dir, identical
  contents), all root-unit binary kinds, and the delete-uplifted-copy
  freshness nuance the tests pin.
- cargo#10: instruction now quotes the exact warning the test pins:
  ignoring `build.fingerprint = "content"` without `-Zchecksum-freshness`.
- cpython#10 / cargo#9 / laravel#2+#11 cascades: fixed generically in the
  runner (failed-dependency gold restoration, `restored_dependencies` recorded
  per turn) — see cli/longrun.py.

Quarantined pending repair (NOT in GOLD, excluded from any scoring):

- rust/rustls_misplaced_extensions (oneshot): compile-class identity binding +
  no fail-to-pass proof; needs the re-base + declare-all-bound-symbols repair.
- laravel#10: compile-class — tests bind to gold's `QueueRoutes::forward()`
  naming (`Call to undefined method`), unstated in the instruction.
- laravel#7: Mockery pins the exact cluster-scan call shape
  (`scan(42, ['127.0.0.1','6379'], '*', 10)`) and `laravel:` key prefix —
  white-box interaction test beyond the stated contract.
- laravel#1 (`Failed asserting that false is true`, context opaque) and
  laravel#6 (retry-count assertion behavioral; RedisExceptions appear
  simulated) remain UNCERTAIN — audit before the sequence scores anywhere.

## Gaps (do not block v1)

1. glm-octomind has no data on 4 of the 10 longrun picks (duckdb, eslint,
   cpython, cargo) — the 5 long sequences were never run on it.
2. Python oneshot slot 4 is weak; the real python splitters
   (`scrapy_http2_frame_size` sol-FAIL, `aiohttp_paused_content_eof` luna-FAIL)
   are 80-corpus-only — swap them in once opencode/octomind run the 80.
3. Audit items that could adjust GOLD scoring: eslint turn 12, cpython turns
   5+10, cargo turns 1/9/10.

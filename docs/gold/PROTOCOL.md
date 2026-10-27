# GOLD selection protocol

Fixed before any calibration run. Changing a rule after calibration data exists
requires a dated amendment below, with the reason, and invalidates selections
made under the old rule.

## What GOLD measures

Per model × client column: **solve rate**, **token efficiency** (fresh input,
cache reads, output, cost), and **speed** (agent wall time), on hard
engineering work where the client's behaviour (navigation, tool-output
handling, verification, context management) changes the outcome or the bill.
Tool-call counts are not comparable across clients because their tools have
different granularity. Heaviness is therefore measured in tokens, not calls.

## Candidate sources

1. The existing corpus: 80 one-shots, 25 long-run sequences.
2. Excluded items repaired under [HARNESS.md](../HARNESS.md) (contract or
   fixture defects listed in the previous GOLD revision): repaired items are
   re-proven and enter as new candidates; their old results do not count.
3. Uncapped sequences: turn caps are not used to remove later, harder turns.
4. Behavioural restatements: an item whose instruction dictates the patch
   (file, function and code-level steps; `spec_level: full-spec`) may be
   restated as the observable failure and required behaviour, with the same
   gold SHA and protected tests. The restatement is a new item: it passes
   Gate V again (every assertion must still trace to the new text) and is
   calibrated afresh; the original item's results do not carry over.
5. Newly harvested cases, only when the rules below leave a quota unfilled.

## Gate V — validity (every candidate, no model calls)

- **V1 proof:** fail at base and pass with gold source on the frozen agent
  image (`scripts/verify_case.sh`, `scripts/verify_longrun.sh`); log kept.
- **V2 determinism:** base validation fails and gold validation passes 3 of 3
  times (`VERIFY_REPEAT=3`).
- **V3 derivability:** every protected assertion traces to the instruction or a
  visible repository convention; a written per-item audit names the sentence
  or convention for each assertion. Assertions that bind private helpers,
  exact patch shape, or wording not in the instruction fail the gate.
- **V4 sealing:** gold source, protected tests and upstream history are
  unreachable from the agent (existing seal + egress allowlist).
- **V5 timing:** validation does not depend on wall-clock races or network.
- **V6 pinned environment:** setup installs dependencies at fixed versions
  (lockfile or explicit pins); an unpinned install lets a later release break
  the gold proof (seen: `anyio_tls_idna2008` fails with gold on the current
  image because `trio`/`trustme`/`pytest` float).

An item failing any gate is repaired and re-proven, or dropped.

**Only the maintainers' tests judge.** Validation runs the upstream tests from
the gold commit, unmodified; GOLD never authors, edits or replaces test code.
A V3 failure is repaired in one of two ways only:

1. **Instruction sentence:** state the behaviour the upstream assertion checks
   (including a public name or message the test calls, when that is what it
   binds), so the assertion becomes derivable.
2. **Test selection:** run a subset of the upstream tests (for example
   deselect one upstream test function that checks something no instruction
   can fairly state), leaving every selected test byte-identical. Allowed only
   when the main checks still run: the selected tests still fail at base and
   still reject a fix that misses the core behaviour. If the deselected test
   is the one that carries the fix, selection is not a repair and the item or
   turn is dropped.

**What "aligned" means (V3).** Tests and task must agree in both directions,
at the level that matters: every upstream assertion follows from the task
(no hidden requirement), a correct solution that differs from gold can pass,
and the tests check the task's core behaviour, so a fix that misses it fails.
Maintainers rarely test every sentence of a real change; an untested
peripheral requirement (for example "preserve existing behaviour X") is
recorded in the audit but does not disqualify the item. An untested core
requirement does: if the simplest partial fix of the main behaviour passes,
the item is dropped.

If neither keeps the item fair and non-trivial, the item or turn is dropped.

**Dropping a long-run turn.** Later turns build on earlier changes, so a
dropped turn becomes an *unscored* turn: the agent does not run, the harness
applies that turn's gold source change (the same path it already uses to
restore a failed turn's prerequisites), and the session continues. Unscored
turns are reported separately and count toward neither solve rate nor
efficiency. A GOLD sequence may contain at most two unscored turns and at most
one in five of its turns; a sequence needing more is dropped.

## Stage P — prior (historical evidence)

`scripts/gold_inventory.py` builds `docs/gold/inventory.*` from every recorded
column. Shortlist: one-shots with historical pass rate below 1.0 or combined
effort index at or above 1.3; sequences with any historically failed turn or a
per-turn token index at or above 1.3; plus every repaired item. Known easy
items (all columns pass, effort index below 1.0) are not shortlisted except
as anchor candidates.

## Stage C — calibration (current model tier, not baseline)

- Model `gpt-6.1-sol`, low reasoning (the bench mapping). Both Codex and
  Octomind supply calibration samples under the same image and settings as
  publication runs.
- Calibration results are selection evidence only; they are never presented as
  GOLD baseline results or reused as GOLD results. Publication rounds are fresh
  runs.
- Every failure is classified (legitimate, case defect, infra, flake,
  undetermined) before it counts. A case defect sends the item back to Gate V.

Admission uses valid samples pooled across both clients, never the direction of
a client gap. A one-shot is retained when either:

- it is heavy: at least roughly 2M total tokens per run, including cache, in
  the pooled valid samples from both clients; or
- it is consistently hard: failures are legitimate misses of a stated rule.

Light items that both clients solve are excluded. Infrastructure, harness-bug,
and pre-repair samples are void and do not affect admission. Tool-call counts
are not an alternative threshold.

After a client failure, an instruction may be changed only when an executed
test checks a requirement that was genuinely absent from both the instruction
and visible repository conventions. The repaired item returns to Gate V and
its earlier samples are void. If the client missed a rule that was already
stated, the failure is a real result; the instruction is not expanded to turn
that failure into a pass.

Sequences are calibrated uncapped on both clients. They must contain at least
eight turns and cross the 200K context window; the same heavy-or-hard bar is
applied to their scored turns and accumulated sessions. Unscored turns do not
contribute calibration outcomes or efficiency.

## Frozen composition

- 13 one-shots across JavaScript, C++, Python, and Rust.
- 2 uncapped 15-turn sequences: DuckDB and ESLint, with one unscored turn in
  each sequence.

## Publication runs

- Frozen versions (image, client binaries, configs) recorded with results.
- Rounds per column: one-shots enough to reach SE(log cost ratio) ≤ 0.05 using
  the calibration variance, minimum 5; sequences minimum 3.
- Compared columns run paired: within a round, every client starts the same
  item at the same moment, the next item starts when all clients have finished,
  and one-shots run before sequences. Item order is the suite file's order.
  Each client's container is pinned to its own equal share of CPU cores under
  the same memory cap with swap off, and the core sets swap between clients
  every round. Each client uses its own
  ChatGPT login session. Pairing removes provider latency drift between
  columns; time ratios are reported only for paired records.
- An infrastructure failure is rerun for the failed client only, into the same
  round directory; that item's time is then unpaired and reported separately.
  Each column records its image, versions and run dates.
- Reported separately, never merged: solve rate with confidence interval;
  paired geometric-mean cost, token and time ratios with confidence intervals
  on items solved by every compared column; all-attempt cost and time per
  solve; matched-item coverage. Long-run turns after a gold restoration are
  reported as assisted.

## Result history

- A run set is one campaign of compared columns under one image and one
  scheduling mode, named `<start date>-<mode>` (for example
  `2026-10-23-paired`). Its per-round records and a scorecard snapshot live in
  `docs/gold/results/<run set>/`.
- The newest complete run set is the default: the GOLD block and the
  frozen-versions table in `BENCHMARK.md` show only that set. Before a new set
  replaces it, the outgoing GOLD block is saved as
  `docs/gold/results/<old run set>/scorecard.md`, and `docs/GOLD.md` lists every
  earlier set with its dates, image and link.
- Nothing is deleted. Raw result directories keep distinct names per run set
  (`results-gold-*` for the sequential set, `results-gold-paired-*` for paired
  sets), and abandoned runs keep an `abandoned-<date>-` prefix.
- Time ratios are compared only within one paired run set. Solve rate, tokens
  and cost from an earlier set may be shown next to the current one only as
  labeled context, never as a column of the current comparison.

## Amendments

- **2026-10-15:** Recorded the threshold used for the freeze: roughly 2M tokens
  per run with valid Codex and Octomind samples pooled, or a legitimate miss of
  a stated rule. Removed tool-call counts because client tool granularity is
  not comparable, and recorded the post-failure instruction rule.
- **2026-10-16:** Infrastructure failures (provider capacity/5xx errors, refusals
  caused by repository contribution policies) are rerun inside the same round
  directory; the newer run directory replaces the void record. Setup of the polars
  and both DuckDB one-shots removes the upstream `AI_POLICY.md`. Short judge panels
  are rejudged before publication (`scripts/rejudge_longrun.py`).
- **2026-10-17:** Long-run judges now receive the unified diff (`build_evidence`, as
  one-shots); earlier long-run judge prompts listed changed paths only, so the
  published judge mean covers one-shots. Each column also publishes a per-round
  record (`scripts/gold_rounds_report.py`) under `docs/gold/results/`. The DuckDB
  sequence setup also removes `AI_POLICY.md` (re-proven); the Codex column ran it
  with the file present and never opened it. Round scheduling: the requirement is
  that clients never run at the same time, not strict round-by-round alternation;
  columns may run their rounds back to back and record their run dates.
- **2026-10-23:** Paired publication rounds replace sequential columns. A
  sequential octomind gpt-6.1-sol run on 2026-10-23 recorded about 11.9 s per
  model call against 7.2 s for Codex at the same hour one week earlier, with the
  same or fewer output tokens, so wall-time ratios between columns run on
  different days measured provider drift, not the clients. Clients now run the
  same item at the same moment on disjoint, equal CPU core sets
  (`OCTOBENCH_DOCKER_CPUSET`; driver `gold_paired.sh`), and the Codex column is
  re-run beside Octomind on the current image. Paired round directories are
  `results-gold-paired-<model>-<client>-r<N>`; the earlier sequential columns
  stay published as they are.
- **2026-10-23 (V3 repair):** `duckdb_parquet_bound_schema` gained instruction
  sentence D10 (keep existing C++ constructors and functions source-compatible;
  their callers, including the unit tests under `test/`, must build unchanged).
  Validation rebuilds the full upstream `test/` tree, and the unchanged upstream
  `test/api/test_multi_file_column_mapper.cpp` calls the existing
  `MultiFileColumnMapper` constructor, so an agent that extended that
  constructor and updated its caller failed on a compile error before any
  protected test ran — a requirement no sentence stated. Re-proven with
  `VERIFY_REPEAT=3` on `octobench-agent:gold10`
  (`/home/box/gold-prove/duckdb_parquet_D10_20261023.log`). Earlier samples of
  this item are void, including the 2026-10-16 sequential Codex column's; the
  paired round-1 records moved to `void-20261023-pre-D10-duckdb_parquet/` and
  the item is rerun paired.
- **2026-10-27:** Every container also runs under the same memory cap, 16 GB
  with swap off (`OCTOBENCH_DOCKER_MEMORY`, exported by `scripts/bench.sh`;
  `cli.main` refuses to run without it). Before, paired containers shared the
  host's 62 GB: a DuckDB debug link at `-j 6` measured 5.9 GB of process memory
  beside 24 GB of page cache while other services had pushed the host 16 GB into
  swap, so one client's build could slow the other's. Each record stores
  `container_oom_kills`; an item whose container recorded an OOM kill is an
  infrastructure failure and is rerun. Uncapped runs are not mixed with capped
  runs in one run set.

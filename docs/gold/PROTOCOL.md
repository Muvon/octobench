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
  the calibration variance, minimum 5; sequences minimum 3. Clients alternate
  round by round (one ChatGPT login is never shared by two running clients);
  item order within a round is the harness's fixed sorted order.
- Reported separately, never merged: solve rate with confidence interval;
  paired geometric-mean cost, token and time ratios with confidence intervals
  on items solved by every compared column; all-attempt cost and time per
  solve; matched-item coverage. Long-run turns after a gold restoration are
  reported as assisted.

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
  record (`scripts/gold_rounds_report.py`) under `docs/gold/results/`.

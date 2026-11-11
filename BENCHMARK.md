# Octobench Real-Commit Benchmark

Comparing coding agents on **real, recent, fail-to-pass-proven tasks** (80
one-shot cases) harvested from merged pull requests in trusted open-source
projects — 5 languages (python, php, rust, cpp, js), scenario mix from
one-line crash fixes to multi-surface features, graded by the projects' own
held-out tests plus an LLM judge.

## What this benchmark measures

**This benchmark compares CLIENTS, not prompts.** Every client is given the same
model, the same system prompt, the same tool categories and the same sealed
environment, so the only thing left varying is the client itself: how it
implements its file and shell primitives, how it manages and compacts context,
how its agent loop decides what to do next and when to stop, and how it feeds
tool results back to the model. That steering is the object under test.

Getting there required removing three things that made earlier rounds
incomparable:

1. **One shared system prompt.** The single source is
   `configs/common/system_prompt.md`, distilled from octomind's
   `developer:general` role — its patterns kept (scope discipline, survey →
   implement → verify, root-cause-not-symptom, the simplicity ladder, surgical
   changes, goal-driven verification, the wrap-up format), its client-specific
   tool names dropped. `scripts/sync_system_prompt.py` writes it into every
   harness config and `--check` fails on drift, so the four cannot diverge.
   Previously each client ran its own stock prompt, which was not a fair
   comparison: `developer:general` explicitly *ordered* the agent to websearch
   the upstream issue, follow it to the merged pull request, and "mirror its
   approach and API contracts EXACTLY" — on a bench built from merged PRs, that
   is an instruction to read the answer key.
2. **Equal prompts, not equal tooling.** Every client gets files + shell, and
   each keeps the exploration capabilities it actually ships — octomind retains
   its structural code search (`structural_search`, `view_signatures`), which no
   other client has. That difference is part of what the benchmark compares: a
   client's tooling is the client. Only two things are taken away, because they
   defeat the benchmark rather than characterise the client — web access (see
   below) and persistent cross-case memory, which would carry state between
   cases.
3. **No route to the answer.** Web search and web fetch are disabled in every
   client, and github is unreachable from the agent's container. Case `setup.sh`
   still needs github to check the repo out, so the block is applied *after*
   setup and before the agent starts. Previously opencode fetched
   `raw.githubusercontent.com/<repo>/main/<file under test>` in 13 of 49 cases
   and copied from it verbatim.

Known residuals that cannot be equalized, and should be read as part of the
client: each client wraps the shared prompt in its own scaffolding (claude
injects environment info; opencode auto-loads a repo's `AGENTS.md`, which 3 of
these repos ship), planning primitives differ in kind, and step/turn ceilings
differ.

## GOLD — 13 one-shots + 2 long-run sequences

The compact set that shows solve rate and efficiency (cost, tokens, wall time)
per model × client: varied one-shot tasks across complexity tiers, plus
long-run sequences that outgrow the model's context window — at the lowest run
cost that still supports a conclusion (see [docs/GOLD.md](docs/GOLD.md) for the
purpose, per-case rationale and exclusions). One suite:
`configs/suites/gold.txt`; run either kind with
`scripts/bench.sh <oneshot|longrun> <client> <model> --suite gold`.

Each column aggregates every recorded round under
[docs/gold/PROTOCOL.md](docs/gold/PROTOCOL.md) (minimum 5 rounds for one-shots,
3 for sequences); a column with fewer rounds is provisional. The per-round
record of each column is in [docs/gold/results/](docs/gold/results/); each item
there links to its case manifest, and [docs/GOLD.md](docs/GOLD.md#frozen-items)
lists every item's upstream PR and prompt style.

Wall time includes the provider route, which the client does not choose. On a ChatGPT
plan login, Codex sends its requests to `chatgpt.com/backend-api/codex`, an endpoint
OpenAI reserves for its own client. Octomind, as a third-party client, must use the
documented route, `api.openai.com/v1/responses`. Measured with the same model, reasoning
effort and prompt, one request through Octomind's route takes 1.14× as long as through
Codex's (95% CI 0.98–1.24), even though Octomind sends about 6.4K fewer input tokens.
Read every Octomind ÷ Codex
time ratio against that baseline: method and raw samples in
[docs/gold/route-latency.md](docs/gold/route-latency.md).

Frozen versions per column:

| Column | Per-round record | Rounds | Image | Client | Model | Run dates |
|---|---|---|---|---|---|---|
| codex gpt-6.1-sol | [codex-gpt-6.1-sol.md](docs/gold/results/codex-gpt-6.1-sol.md) | 5 of 5 (SE(log cost ratio) 0.046 ≤ 0.05) | `octobench-agent:gold29` | codex-cli 0.167.0 | gpt-6.1-sol | 2026-11-08 – 2026-11-10 |
| octomind gpt-6.1-sol | [octomind-gpt-6.1-sol.md](docs/gold/results/octomind-gpt-6.1-sol.md) | 5 of 5 | `octobench-agent:gold29` | octomind 0.70.1 | gpt-6.1-sol | 2026-11-08 – 2026-11-10 |

<!-- GOLD:BEGIN — regenerated by scripts/gold_scorecard.py --markers=GOLD; do not hand-edit -->
| metric | codex gpt-6.1-sol | octomind gpt-6.1-sol |
|---|---|---|
| rounds | 5 | 5 |
| solve — one-shot pass rate | 58.5% (95% CI 46.3%–69.6%) · 38/65 pooled | 58.5% (95% CI 46.3%–69.6%) · 38/65 pooled |
| solve — long-run mean sequence pass rate | 100.0% (100.0%–100.0%) · 2.0 sequences mean (2–2) | 100.0% (100.0%–100.0%) · 2.0 sequences mean (2–2) |
| solve — long-run turns passed/total | 100.0% (95% CI 97.3%–100.0%) · 140/140 pooled | 100.0% (95% CI 97.3%–100.0%) · 140/140 pooled |
| solve — assisted long-run turns passed/total | 85/85 pooled | 85/85 pooled |
| not scored — long-run turns | 2.0 (2.0–2.0) | 2.0 (2.0–2.0) |
| diagnostic only — judge mean (one-shots) | 69.1 (65.7–74.6) | 68.7 (66.2–70.7) |
| diagnostic only — harness efficiency score (0–100) | 14.8 (14.3–15.3) | 16.7 (15.8–18.0) |
| efficiency-only headline — matched work cost/time index | 0.99 (0.96–1.02) | 0.96 (0.92–0.98) |
| efficiency — all attempts — cost per solve | $0.59 ($0.51–$0.64) | $0.45 ($0.44–$0.48) |
| efficiency — all attempts — wall time per solve | 0.13h (0.12h–0.14h) | 0.13h (0.13h–0.14h) |
| efficiency — all attempts — tokens per solve | 3.4M (3.0M–3.8M) | 2.2M (2.0M–2.3M) |
| efficiency — all attempts — burn rate | $4.54/h ($4.12/h–$4.96/h) | $3.44/h ($3.23/h–$3.56/h) |
| efficiency — all attempts — active share | 99.7% (99.6%–99.7%) | 96.6% (96.1%–97.0%) |
| efficiency — all attempts — idle time | 0.0h (0.0h–0.0h) | 0.2h (0.1h–0.2h) |
| efficiency — all attempts — own-job wait | 0.00h (0.00h–0.00h) | 2.00h (1.81h–2.13h) |
| efficiency — all attempts — stuck wait | 0.00h (0.00h–0.00h) | 0.00h (0.00h–0.00h) |
| efficiency — all attempts — waste share | 1.9% (0.8%–2.6%) | 0.4% (0.2%–0.7%) |
| efficiency — all attempts — mean tail after final answer | 0.6s (0.4s–0.9s) | 6.7s (6.0s–7.6s) |
| efficiency — all attempts — longest silent gap | 7.5s (4.2s–11.2s) · ≥5m: 0.0 (0.0–0.0) records | 23.6s (12.7s–30.9s) · ≥5m: 0.0 (0.0–0.0) records |
| efficiency — all attempts — cost | $20.89 ($18.87–$22.57) | $16.05 ($15.80–$16.77) |
| efficiency — all attempts — fresh input tokens | 2.1M (1.8M–2.4M) | 2.5M (2.4M–2.6M) |
| efficiency — all attempts — cache read tokens | 119.8M (109.3M–128.5M) | 73.7M (70.6M–78.7M) |
| efficiency — all attempts — output tokens | 478K (431K–499K) | 253K (248K–263K) |
| efficiency — all attempts — reasoning tokens (codex: subset of output) | 196K (160K–208K) | 96K (87K–101K) |
| efficiency — all attempts — total tokens | 122.4M (111.5M–131.4M) | 76.6M (73.5M–81.6M) |
| efficiency — all attempts — agent time | 4.6h (4.3h–4.8h) | 4.7h (4.5h–4.9h) |
| efficiency — matched work items | 34.8 (34.0–36.0) | 34.8 (34.0–36.0) |
| efficiency — matched work — cost | $12.21 ($10.26–$14.24) | $9.34 ($7.91–$10.00) |
| efficiency — matched work — fresh input tokens | 1.3M (1.0M–1.5M) | 1.4M (1.2M–1.6M) |
| efficiency — matched work — cache read tokens | 70.0M (59.0M–81.2M) | 42.9M (36.0M–46.8M) |
| efficiency — matched work — output tokens | 271K (229K–306K) | 157K (139K–164K) |
| efficiency — matched work — reasoning tokens (codex: subset of output) | 104K (79K–118K) | 52K (41K–64K) |
| efficiency — matched work — total tokens | 71.5M (60.3M–83.1M) | 44.5M (37.4M–48.4M) |
| efficiency — matched work — agent time | 2.5h (2.2h–2.7h) | 2.6h (2.3h–2.8h) |
| efficiency — matched work — relative cost index | 1.05 (95% CI 1.02–1.08) | 0.89 (95% CI 0.86–0.93) |
| efficiency — matched work — zero-cost items excluded from relative index | 0 (0–0) | 0 (0–0) |
| efficiency — matched work — relative time index | 0.94 (95% CI 0.92–0.97) | 1.02 (95% CI 0.99–1.05) |
| efficiency — matched work — zero-time items excluded from relative index | 0 (0–0) | 0 (0–0) |
| efficiency — matched work — relative token index | 1.10 (95% CI 1.06–1.15) | 0.80 (95% CI 0.75–0.85) |
| efficiency — matched work — zero-token items excluded from relative index | 0 (0–0) | 0 (0–0) |

_Most totals and all-attempt metrics are per-round means (min–max); pooled rates and confidence intervals are labeled. Long-run solve rate gives every sequence equal weight; turn counts are shown separately. Matched work contains only one-shot cases and long-run turns solved by every reported column in the same round. Agent time excludes setup, validation, and judging. Cost, wall time per solve, and burn rate include all attempts. Active share is the union of model, tool, and completed own-job intervals divided by wall time; idle time is the remainder. Own-job wait counts only delivered jobs; stuck-job wait reports launched jobs without a completion. Longest silent gap is the largest contiguous idle interval and includes the count of records at or above five minutes. Codex model intervals run from task start, turn context, or completed tool output through the response's token-usage record; tool intervals pair function/custom-tool calls with outputs by call ID. Waste counts repeat plus filler calls over all tool calls. Tail is provider exit minus the final assistant message. Relative indexes divide each matched item by its across-column median, then take the per-column geometric mean (1.00 is typical); their 95% confidence intervals use 10,000 fixed-seed bootstrap resamples of paired matched item-round observations. With one column, every relative index is 1.00 by definition and becomes meaningful only when another column is added. Zero-valued items are excluded because log(0) is undefined, with exclusion counts reported in the table. Solve-rate confidence intervals are pooled Wilson 95% intervals. The efficiency-only headline is the geometric mean of matched-work relative cost and wall-time indexes; lower is better, and wall time already carries all waiting. Assisted turns remain in the scored totals; the protocol excludes only unscored turns, which ‘count toward neither solve rate nor efficiency.’ Unscored long-run turns are listed separately and excluded from solve, judge, efficiency, and matched-work metrics. Total tokens are fresh input + cache read + output, plus reasoning only where a client reports it separately; Codex output already includes its reasoning tokens. Missing client evidence is UNKNOWN, never zero. Judge mean is diagnostic only and covers one-shots: long-run judge prompts before 2026-10-17 listed changed paths without the diff. The harness efficiency score is the mean over scored runs of compute_efficiency_score (0–100; exponential decay of agent time and cost against the scoring config references); it is diagnostic and absolute, not a comparison. GOLD never merges solve and efficiency._
<!-- GOLD:END -->

## What a case is

Each case in `cases/dev/oneshot/<language>/<case>/` reconstructs a real merged PR as a
task (see `AGENTS.md` → "Real-Commit Case Harvesting" for the full pipeline and
rules):

- **`case.yaml`** — the task `instruction` plus `meta` (repo, base/gold SHAs,
  PR/issue links, held-out `test_paths`). Three prompt scenarios exist: a
  reverse-engineered spec via the `developer:reverse-spec` tap agent (default),
  the original GitHub issue text verbatim (`prompt_source: original-issue`),
  and a short casual developer ask, the way a person would type it to an agent
  (`prompt_source: human-prompt` — used only for fixes whose correct behavior
  is unambiguous from the symptom plus repo conventions).
- **`setup.sh`** — shallow-fetches the pre-fix BASE commit (single reachable
  commit: the fix is not in the object store), prepares the toolchain
  (pip/composer/npm/cargo/cmake), removes the git remote.
- **`validate.sh`** — after the agent runs, fetches the gold commit and checks
  out ONLY the held-out test paths (agent edits to tests are overwritten), then
  runs those tests selectively. Non-zero exit = task failed.
- **`quality.sh`** — cheap objective build/lint sanity.

Every case is proven **fail-to-pass** before benching
(`scripts/verify_case.sh <case_dir>`): tests must fail at BASE and pass with the
real merged fix applied. Every held-out assertion was audited to be derivable
from the instruction (no grading on undisclosed prose/formatting picks).

## Scoring

Per case, the stored diagnostic final score combines hidden-test validation
(hard pass/fail, with a 25-point failure penalty), an LLM judge score from
0-100 (judge = octomind `judge` role), and an efficiency component based only
on agent latency and cost. Token counts are reported directly; tokens per
second is not rewarded. The diagnostic score is not a ranking metric.

GOLD reports solve rate and efficiency separately for each model × client,
using three full rounds per column. One-shot cases and long-run sequences have
separate solve rates, long-run sequences receive equal weight, and efficiency
is shown both for every attempt and for work solved by every reported column.
Judge mean is diagnostic only; GOLD has no combined Σ final score.

The judge is a **3-model panel**
(`OCTOBENCH_JUDGE_MODELS`, comma-separated — currently
thinkingmachines/inkling-small, minimax/minimax-m3 and
deepseek/deepseek-v4-flash-0731 via OpenRouter): each model judges the same
evidence independently and in parallel, the recorded score/confidence is their
mean, and per-judge verdicts are kept in the record under `judge.judges` (a
judge that fails to produce a verdict is excluded from the mean, never zeroed
into it). `OCTOBENCH_JUDGE_MODEL` (singular) still selects a single-model
judge. Costs: claude reports its own `total_cost_usd` (correct 1h-cache-write
pricing); other providers are priced from token counts × `configs/models.yaml`.

## Reproduce

On a linux host with docker (agents authenticate via env keys + mounted CLI
logins — see `runners/executor.py` `AUTH_ENV_KEYS`):

```bash
# 1. Agent image (toolchains for all 5 languages + pinned agent CLIs)
docker build -f docker/Dockerfile.agent -t octobench-agent:latest docker

# 2. Prove every case fail-to-pass (optional but recommended)
for c in cases/dev/oneshot/*/*; do scripts/verify_case.sh "$c"; done

# 3. Clean-bench switches — REQUIRED for a cross-client comparison.
#    Without them each client runs its own prompt, tools and web access, and the
#    columns are not comparable (see "What this benchmark measures").
python scripts/sync_system_prompt.py --check     # fails if the four have drifted
export OCTOBENCH_SYSTEM_PROMPT=configs/common/system_prompt.md  # claude + codex
export OCTOBENCH_SEAL_NETWORK=1                  # github unreachable to the agent
export OCTOMIND_AGENT=developer                  # shared-prompt role, not developer:general
# octomind + opencode take the prompt from their configs, which the sync writes.

# 4. Run per provider (see run_full_*.sh for the exact wrappers used)
export OCTOBENCH_JUDGE_MODEL=ollama:minimax-m3
python -m cli.main run --cases cases/dev/oneshot --config configs/run-matrix.cases-claude.yaml \
  --executor docker --image octobench-agent:latest --out results-full-claude
# same with run-matrix.cases-octomind.yaml / run-matrix.cases-codex.yaml

# 5. Retry infra failures (provider 5xx etc.) and repair degenerate judge verdicts
python scripts/rerun_failed.py results-full-claude/<ts>/results.json configs/run-matrix.cases-claude.yaml
python scripts/rejudge.py     results-full-claude/<ts>/results.json
```

## Case collection (adding more)

`scripts/reverse_spec.sh <repo_url> <gold_sha> [out.md]` reconstructs the task
from a merged commit via the `developer:reverse-spec` agent; curate its Task
Prompt (plus the spec requirements whenever hidden tests pin API names, wire
formats, or exact output) into `case.yaml`. For issue-driven cases use the
original issue text, trimmed of fix-leaking sections. Full criteria and the
derivability rule: `AGENTS.md` → "Real-Commit Case Harvesting".

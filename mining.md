# Mine the Next 10 Octobench Cases: Public Workflows and Black-Box Contracts

You are working in the Octobench repository. Read `AGENTS.md` first, then read
`docs/USAGE.md`, `docs/ARCHITECTURE.md`, and `docs/EXTENDING.md`. Inspect the
current `cases/dev` corpus before searching. Do not rely on an old inventory or
assume which repositories, scenarios, or prompt styles are already represented.

Your first assignment is **research and selection only**. Mine the next 10
real-commit development cases, present the evidence-backed shortlist, and stop
for approval. Do not create case directories or change the Docker image during
this phase.

## Goal

Find exactly 10 recent, human-solved tasks:

- 2 C++
- 2 JavaScript/TypeScript
- 2 PHP
- 2 Python
- 2 Rust

This batch must occupy a different part of the benchmark than the current
library-internal, parser, crash, and isolated algorithm cases. Call this batch
**public workflow / black-box contract**.

The defining property is that a normal user, application developer, operator,
or integrator can describe and observe the failure through a supported public
surface. Good surfaces include:

- a CLI invocation, flags, stdin/stdout/stderr, exit status, or generated file;
- documented configuration, environment variables, config precedence, or a
  reload/restart boundary;
- an HTTP request/response, public SDK call, serialization format, or protocol
  exchange;
- filesystem behavior such as paths, permissions, atomic replacement, cleanup,
  caching, or generated artifacts;
- a multi-step lifecycle such as connect/use/disconnect, start/cancel/retry,
  create/update/delete, save/reload, or fail/recover;
- backward compatibility across two supported representations, modes, or
  versions.

The implementation may be deep inside the project, but the task and acceptance
tests must be expressible using public behavior. Reject changes whose only
meaningful assertion is about a private helper, internal class name, chosen data
structure, or maintainer taste.

## Two New Prompt Lanes per Language

Select exactly one case from each lane for each language. That gives two cases
per language and ten total.

### Lane A: Support Ticket Reproduction

Write the task like a real support ticket from a user who encountered a broken
workflow. It should contain:

- what the user was trying to accomplish;
- a minimal realistic invocation, request, config fragment, or short sequence;
- the actual observable result;
- the expected observable result;
- only the environmental detail needed to disambiguate the behavior.

The prompt should normally be 4-8 sentences. It may include a small command,
request, config, or code fragment if a user would naturally include one. Do not
name the fix, changed source file, private helper, algorithm, or gold commit.

This is not the previous "one-sentence human prompt" style. It is an authentic
problem report with enough reproduction detail to let an engineer investigate.

### Lane B: Acceptance Story

Write the task as a product/QA acceptance story using behavior-level scenarios.
Start with the user or operator goal, then give 3-6 compact Given/When/Then
scenarios or equivalent acceptance bullets. Include at least:

- the main corrected workflow;
- one adjacent mode or representation that must remain compatible;
- one failure, cleanup, retry, restart, cancellation, or idempotency path;
- one boundary case that prevents a shallow special-case solution.

All requirements must be externally observable. Do not prescribe architecture
or mirror the gold diff. This lane should test whether an agent can reason across
a sequence of user actions, not merely patch one input/output example.

## Target Behaviors Missing from the Current Corpus

Across the final ten, cover at least six of these categories, with no category
used more than twice:

1. CLI exit status plus stdout/stderr behavior.
2. Configuration or environment-variable precedence.
3. Filesystem artifact creation, cleanup, atomicity, or path handling.
4. Retry/reconnect/restart behavior after a partial failure.
5. Backward compatibility between two public formats or modes.
6. Idempotency when a user repeats an operation.
7. Cancellation, shutdown, or timeout visible to the caller.
8. Public HTTP/API validation, status, headers, or response body.
9. State persistence or save/reload round-trip.
10. Cross-platform behavior that is deterministic in Linux containers.
11. Unicode, locale, time-zone, or path behavior in a complete user workflow.
12. Resource ownership that is observable through a public lifecycle.

Do not fill the batch with ten variations of malformed-input validation. Do not
use more than two parser/encoding tasks, and accept those only when embedded in
a larger public workflow.

## Mandatory Candidate Criteria

Every selected case must satisfy all of the following.

### Recency and contamination control

- Recency is the first filter, not a tie-breaker.
- Determine the newest benchmark model represented by the active Octobench
  configuration and identify its documented training cutoff if that information
  is available from an authoritative source.
- Do not invent a cutoff. State the cutoff and source you used. If no trustworthy
  exact cutoff is available, state that limitation and use the newest practical
  merge window as a conservative policy, preferring PRs merged in the last 30
  days.
- Every final PR must have merged after the chosen contamination boundary.
- Prefer the newest valid cases. An older famous PR does not beat a newer valid
  one merely because its repository has more stars.

### Proven human work

- The production fix must be authored by a human, not a bot-generated dependency
  update or automated rewrite.
- It must be merged into the upstream default or active release branch.
- Record evidence of real review: approving reviewers, maintainer discussion,
  requested changes resolved, issue reporter confirmation, release-note entry,
  or equivalent evidence.
- CI must have run on the change, and the relevant test suite must have passed.
- Prefer fixes with a linked user report, reproduction, or maintainer-confirmed
  regression.
- A merged PR alone is insufficient proof. Explain why the change is credible
  human-solved work.

### Repository quality

- Use respected, actively maintained repositories with meaningful adoption,
  real review, and real CI.
- Stars are supporting evidence, not the sole quality signal. Also inspect recent
  release activity, maintainer involvement, review depth, and downstream use.
- Use ten repositories that do not already appear anywhere under
  `cases/dev/*/*/case.yaml`. Do not reuse a repository in this batch.
- Prefer a mix of foundations, globally recognized companies, and mature
  independent projects rather than ten projects from one ecosystem or owner.

### Change quality

- The gold change must touch production source and tests.
- Reject reverts, documentation-only work, refactors without a behavior change,
  CI-only work, formatting, dependency bumps, generated-code-only changes, and
  performance-only changes without a deterministic correctness contract.
- Prefer focused changes: roughly 5-200 changed production lines is ideal. A
  larger change is acceptable only when the selectively runnable acceptance
  surface is still narrow and derivable.
- The task must require genuine investigation and at least one non-trivial edit.
  Reject typo fixes and tasks solvable by blindly copying an error string.
- Favor changes crossing a meaningful boundary: parsing to execution, config to
  runtime, public API to state, request to response, or lifecycle event to
  cleanup.

### Testability

- Gold tests must be deterministic, offline at validation time, and selectively
  runnable by file, test name, or narrow package target.
- The toolchain must exist in `docker/Dockerfile.agent`, or the required addition
  must be small, stable, and justified.
- Reject cases requiring cloud credentials, browsers with large downloads,
  external databases/services, privileged containers, flaky timing, special
  hardware, proprietary fixtures, or a full multi-hour suite.
- A local loopback server, temporary directory, fake clock, in-memory transport,
  or project-provided test double is acceptable.
- Estimate setup time, validation time, disk use, and any extra system packages.

## Derivability Audit: Required Before Selection

Read every new or modified gold test that would be hidden. For each assertion,
classify it as one of:

- directly stated by the proposed task;
- necessarily implied by the stated public contract;
- existing documented/project behavior that the task explicitly says to
  preserve;
- not derivable.

Reject the case if a necessary assertion is not derivable. Do not repair a bad
case by leaking implementation details into the prompt. Pay special attention
to exact error prose, ordering, whitespace, path normalization, header values,
exit codes, default values, timing thresholds, and internal names.

Public codes, flags, exception types, fields, headers, and documented wire
formats may be stated when the contract requires them. Maintainer-chosen private
names may not.

For each final candidate, provide a compact assertion matrix:

| Hidden assertion | Prompt sentence/scenario that makes it derivable |
|---|---|
| ... | ... |

If the matrix needs hand-waving, reject the candidate.

## Base/Gold and Harness Feasibility Audit

Before recommending a candidate:

1. Resolve the exact merged gold SHA and its first parent/base SHA.
2. Confirm the base SHA is the true pre-change state for the production diff.
3. List every changed production path and every candidate hidden test path.
4. Inspect whether the gold test file also contains pre-existing regression
   coverage that will run selectively.
5. Write the exact planned setup, quality, and validation commands.
6. Establish that checking out only the gold test paths at the base should fail
   for the intended reason.
7. Establish that applying only the first-parent gold production diff, excluding
   hidden test paths, should pass.
8. Identify generated files, lockfiles, submodules, large downloads, or build
   steps that could make before/after evidence noisy or leak the solution.
9. Check that the gold commit will not be reachable in the initial workspace.

Do not claim fail-to-pass is proven during mining unless you actually executed
both legs. Label evidence honestly as inspected, command-checked, or fully
executed.

## Leak and Prompt Hygiene

- The initial workspace may contain only the base commit. Gold must not exist in
  its object store until `validate.sh`.
- Hidden gold tests must not be present during the agent run.
- Do not put PR numbers, issue links, commit SHAs, source filenames, test names,
  private symbol names, or maintainer discussion into the task instruction.
- Provenance belongs in `case.yaml` metadata, not in the instruction.
- Do not let setup logs, cached patch files, generated snapshots, package-manager
  metadata, or repository remotes reveal gold.
- The task must read like something a real user, operator, integrator, QA
  engineer, or product engineer would send to a coding agent.

## Diversity Rules

The final ten must satisfy all of these:

- exactly one Lane A and one Lane B case per language;
- ten different repositories, all new to the current corpus;
- at least six target behavior categories from the list above;
- at least three cases whose public reproduction spans multiple operations;
- at least three cases involving a failure/recovery or cleanup path;
- at least two compatibility/default-preservation cases;
- at least two small gold production diffs (under about 30 changed lines);
- at least two medium multi-file fixes;
- no more than two security cases;
- no more than two parsing/encoding cases;
- no more than two cases from the same GitHub organization;
- no two cases with essentially the same failure mechanism.

Do not force a weak language candidate merely to complete the matrix. Mine
alternates and explain if one slot remains below the bar.

## Search Strategy

Search broadly before selecting:

1. Build a live inventory of current repositories, case names, scenarios,
   prompt sources, and test commands under `cases/dev`.
2. For each language, inspect recently merged PRs in at least six strong
   repositories not already used by Octobench.
3. Search issue labels and PR titles for user-visible terms such as regression,
   CLI, config, reload, retry, reconnect, cleanup, shutdown, exit code, header,
   response, path, cache, migration, compatibility, idempotent, timeout, and
   cancellation.
4. Read the linked issue and review discussion before reading only the patch;
   determine the user story independently of the implementation.
5. Inspect the full first-parent diff and all changed tests.
6. Keep at least two viable alternates per language until the final cross-language
   diversity pass.

Do not select by title or star count alone.

## Required Mining Report

Return a detailed report with these sections.

### 1. Current-corpus gap analysis

Summarize what is already well represented and why this public-workflow batch is
materially different. Include counts from the live tree.

### 2. Contamination boundary

Name the newest configured model, the cutoff or conservative merge window used,
the authoritative source if one exists, and any uncertainty.

### 3. Broad search log

For each language, list the repositories searched and briefly state why major
candidates were accepted or rejected. Include enough rejected candidates to
show the search was not cherry-picked around the first result.

### 4. Final ten

Provide one row per selected case:

| Lang | Lane | Repository | PR and issue | Merged at | Human/review proof | User-visible workflow | Scenario category | Base SHA | Gold SHA | Production paths | Hidden test paths | Selective test command | Estimated setup/validation | Why it is new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Use full links and full 40-character SHAs.

### 5. Proposed task instructions

Write the exact user-facing instruction for every case. Lane A must read like a
support ticket. Lane B must read like an acceptance story. These are draft
instructions, not summaries.

### 6. Derivability matrices

Include the assertion-to-prompt matrix for each case. Quote or tightly paraphrase
assertions without copying large copyrighted test bodies.

### 7. Harness plans

For each case, give:

- planned case directory name;
- `setup.sh` dependency/build strategy;
- cheap `quality.sh` command;
- exact `validate.sh` test command;
- gold test paths to overwrite at validation time;
- source paths expected from the first-parent diff;
- Docker/toolchain changes, if any;
- likely runtime and risk notes.

### 8. Alternates and rejection reasons

Give at least two alternates per language. State the concrete reason each lost:
older merge, weak public surface, derivability leak, non-selective tests, flaky
timing, external service, gold already contaminated, too large, bot-authored, or
insufficient human review.

### 9. Recommendation and stop gate

Rank the ten by expected benchmark value and flag any case that has not yet had
its commands executed. Then stop and ask for approval. Do not implement cases
until explicitly asked.

## Quality Bar

The result should make it possible for another engineer to challenge every
selection. Prefer nine excellent cases plus one clearly flagged unresolved slot
over silently lowering the standard. Never call a task valid merely because the
gold patch has tests: prove that the tests express a public, user-derivable
contract and that Octobench can hide and run them without leaks.

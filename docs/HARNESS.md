# Real-Commit Harnessing Protocol

This document is the authoritative protocol for finding, constructing,
validating, running, auditing, and finalizing real-commit development cases for
a requested client/model. It applies to both [one-shot cases](ONESHOT.md) and
[long-run sequences](LONGRUN.md).

`HARNESS.md` defines whether a case is valid and useful. The one-shot and
long-run documents define the mechanics specific to each format.

Normative terms are used deliberately:

- **MUST** is an admission requirement.
- **SHOULD** is the default; exceptions need a recorded reason.
- **MAY** is optional.

## Purpose

Harnessing is an end-to-end assignment, not just case preparation. For every
task requested by the user, the work continues through candidate construction,
mechanical proof, execution on the requested client/model, trace and patch
audit, correction of any harness defect, and a trustworthy final classification.
A legitimate model failure is a valid final result; the protocol does not tune
the case until the model passes.

Octobench measures whether an agent can finish realistic software-engineering
work to the behavior expected by project maintainers. The target is not exact
patch reproduction. The gold commit supplies provenance and an objective
behavioral reference; any independently correct implementation must be able to
pass.

The governing principle is:

> A hard case must be difficult because of the engineering work, not because
> the prompt is incomplete, the validation is arbitrary, the environment is
> broken, or the answer is exposed.

The complete corpus should remain balanced. New harvesting should preferentially
add cases that discriminate between capable frontier models: work that requires
real investigation, repository understanding, careful implementation, and a
complete fix. Existing valid easier cases remain useful for breadth, regression
tracking, and lower capability tiers.

## Supported scope

The currently supported development languages are:

- Python
- JavaScript and TypeScript
- Rust
- C++
- PHP

A case MUST use a toolchain available in `docker/Dockerfile.agent`. A new
language or build system is admitted only after the image supports its compiler,
package manager, build dependencies, and selective test execution.

Development cases come in two forms:

- **One-shot:** one repository state, one instruction, one agent attempt, and
  one objective validation contract.
- **Long-run:** multiple chronological tasks in one repository and one resumed
  session, with source changes and learned context persisting across turns.

## 1. Define the harnessing request before mining

Before selecting candidates, record:

- the requested client, provider, model, and checked-in run configuration;
- the newest relevant model cutoff that is publicly known;
- the desired languages and missing corpus dimensions;
- whether the campaign targets general balance, a hard tier, or long-run
  continuity;
- the runtime and toolchain constraints of the agent image.

The requested client/model is part of the completion contract. If the user asks
only for construction and explicitly defers execution, the result is a draft
case, not a finalized harnessed case.

Model performance helps classify case difficulty, but it does not define
correctness or fairness.

## 2. Mine credible real work

Candidate changes MUST come from merged work in an established open-source
repository. By default, repositories should be widely known and have strong
public adoption signals such as stars, downloads, dependents, or ecosystem use.
They must also be:

- widely used and recognizable;
- actively maintained and released;
- reviewed by maintainers with a meaningful quality bar;
- protected by real CI and deterministic tests;
- large enough that repository navigation and local conventions matter.

Stars are useful evidence, but stars alone are not proof of project quality. A
less famous project is an exception and requires a documented reason plus
stronger evidence of maintenance, review, real usage, and test quality.

The candidate itself MUST:

- be merged, not merely proposed or closed;
- change production source and tests;
- represent user-visible, developer-visible, correctness, reliability,
  compatibility, performance, or maintainability behavior;
- have tests that can run selectively without network access;
- avoid flaky timing, external services, mutable data, and unavailable hardware;
- be separable from unrelated changes in the same merge.

Reject documentation-only, CI-only, formatting-only, generated-only, revert,
version-bump, and broad mechanical-refactor changes unless the campaign
explicitly measures that kind of work.

## 3. Prefer freshness and assess human provenance

Freshness is the primary contamination defense. A candidate SHOULD be merged
after the documented training cutoff of the newest model being evaluated. If a
cutoff is unknown, use the newest practical merge window and record that the
contamination risk is unknown rather than claiming the case is unseen.

The implementation MUST have credible human provenance. Review:

- the PR author and repository contribution history;
- review discussion and iteration;
- commit authorship and co-authorship markers;
- bot labels or declared AI-agent use;
- suspicious mass-generated changes or templated explanations;
- whether the tests and implementation form a coherent maintainer-reviewed
  change.

Reject declared bot- or AI-authored implementations and candidates with strong
AI-generation signals. Absence of a fingerprint is not absolute proof of human
authorship; record this as a provenance assessment, not a certainty.

## 4. Establish exact provenance

Every newly harnessed case MUST record the following in its manifest or final
harnessing report:

- repository URL;
- PR URL, or a commit URL only when no PR record exists;
- issue URL when the instruction derives from an issue;
- exact base SHA;
- exact gold SHA;
- target branch;
- validation test paths and their visibility;
- prompt source/style and task classification.

The gold SHA MUST be the true merged commit reachable from the intended target
branch, not a PR branch-head SHA. In multi-branch repositories, reachability
from the default branch is insufficient: confirm that every selected change
targets the same intended branch lineage.

The base MUST represent the repository immediately before the selected behavior
change. For long-run sequences, use a valid common starting point and verify the
turns cumulatively in chronological order.

### Case identity and metadata

Names must describe the engineering task, not the harvesting campaign.

- The directory slug SHOULD be `<project>_<short_behavior>`, using only the
  minimum words needed to identify the task.
- Do not repeat hierarchy already expressed by `cases/dev/oneshot/<language>/`
  or `cases/dev/longrun/<language>/` in the directory name.
- Do not add arbitrary `dev2`, batch, round, date, model, provider, pass/fail,
  or difficulty prefixes.
- The manifest `id` MUST be stable and globally unique. Prefer a concise form
  such as `<language>_<project>_<short_behavior>` when a project-qualified slug
  alone is not globally unique.
- The human-readable `name` MUST summarize the actual requested behavior in
  plain language.
- `task_type` MUST identify the primary engineering task using the taxonomy
  below. Narrow technical dimensions belong in `capability_tags`, not in a
  one-off task type.
- `prompt_source` and optional `prompt_style` MUST truthfully describe how the
  final instruction was reconstructed. Composite prompts must not be labeled as
  verbatim original issues.
- `difficulty` MUST reflect expected engineering investigation and
  implementation effort, not prompt length or the requested model's outcome.
- Provenance, test paths, prompt metadata, and classification metadata MUST describe
  the same selected change. Copying stale metadata from another case is an
  admission failure.

Do not rename an already published legacy case casually because its identifier
keys historical results. Normalize legacy naming only as an explicit versioned
migration; apply this naming contract to every new case.

## 5. Build a realistic and balanced task mix

Balance is multi-dimensional. Review the corpus across:

- language and build system;
- repository and application domain;
- implementation size and expected investigation time;
- task type: bug, feature, behavior change, performance, refactor, or maintenance;
- capability: crash, regression, compatibility, concurrency,
  lifecycle, parser edge, data correctness, or performance;
- prompt style and amount of context;
- subsystem breadth and number of interacting components;
- observed frontier-model outcomes.

Do not fill a campaign with many near-identical easy edits merely to reach a
case count. Do not fill it exclusively with large features either. Real work
contains both, while the hard tier should favor cases that require sustained
reasoning and expose incomplete or subtly incorrect fixes.

Difficulty describes expected engineering effort, not prompt length, gold diff
size, or whether one particular model passed. A one-line source fix can require
complex diagnosis; a large mechanical implementation can be straightforward.

### Required classification tags

Every finalized one-shot task and every long-run turn MUST carry these
orthogonal classifications:

```yaml
difficulty: medium                 # simple | medium | complex | expert
meta:
  task_type: bug-fix
  failure_modes: [crash]
  prompt_source: original-issue
  prompt_style: reproduction-report
  spec_level: symptom-led
  test_visibility: mixed
  capability_tags: [debugging, parser, regression]
```

Long-run sequences put `difficulty`, `task_type`, `failure_modes`, `prompt_source`,
`prompt_style`, `spec_level`, `test_visibility`, and `capability_tags` on each
turn because complexity and interaction style can change during the session.
Sequence-level metadata describes the shared repository and continuity theme.

Use the following complexity rubric:

- `simple` — localized behavior, little investigation, and few interacting
  constraints. It may still catch careless implementations.
- `medium` — meaningful diagnosis, multiple edge cases, or coordinated changes
  across a small number of components.
- `complex` — non-local reasoning, subtle state or lifecycle interactions, or
  several coupled correctness constraints.
- `expert` — sustained cross-subsystem or architectural reasoning, deep domain
  knowledge, difficult concurrency/protocol work, or a long investigation that
  would challenge an experienced human. Use this rarely.

Use one primary `task_type`:

- `bug-fix` — incorrect existing behavior, including crashes and regressions;
- `feature` — a new user- or developer-visible capability;
- `behavior-change` — an intentional change to an existing contract;
- `performance` — bounded work, allocation, latency, or resource improvement;
- `refactor` — behavior-preserving structural improvement with objective proof;
- `maintenance` — reliability, compatibility, or technical-debt work that does
  not fit the categories above.

Use `failure_modes` to describe what is observably wrong before a corrective
task. This is a list because real defects can overlap:

- `crash` — process termination, panic, fatal exception, or abort;
- `wrong-result` — successful execution produces incorrect behavior or output;
- `rejected-valid-input` — valid input, state, or configuration is rejected;
- `accepted-invalid-input` — invalid or unsafe input is incorrectly accepted;
- `hang` — deadlock, livelock, infinite loop, or failure to make progress;
- `race` — timing-dependent incorrect behavior;
- `resource-leak` — memory, handles, tasks, connections, or processes remain
  live incorrectly;
- `data-loss` — data is dropped, corrupted, or irreversibly overwritten;
- `security` — confidentiality, integrity, authorization, or injection failure;
- `compatibility` — an existing supported contract or platform stops working;
- `performance-regression` — work, allocation, latency, or resource use regresses;
- `build-failure` — compilation, linking, packaging, or deterministic tests fail.

Use `failure_modes: []` for a new feature or another task with no pre-existing
failure. Do not infer a crash merely because a test process exits non-zero; tag
the user-visible or developer-visible failure the task actually repairs.

Use `capability_tags` for the concrete engineering demands. Keep the list short
and prefer reusable terms such as `debugging`, `repository-navigation`,
`cross-file`, `api-design`, `parser`, `concurrency`, `lifecycle`, `security`,
`compatibility`, `serialization`, `state-management`, `performance`, or
`build-system`.

Difficulty, task type, failure modes, and capability tags are assigned from the task itself
before looking at the requested client's result. A model pass or failure does
not rewrite them.

## 6. Preserve realistic prompt variety

Prompt style and implementation complexity are independent axes. Use the prompt
form that could realistically have initiated the original work.

The task MAY be reconstructed from any trustworthy combination of:

- the original issue or support report;
- the PR description and maintainer discussion;
- review feedback and acceptance notes;
- the gold tests and observable behavior they enforce;
- the production solution, used to understand the affected flow;
- a reverse-spec analysis of the merged change.

These sources are evidence for reconstructing the task, not text that must be
copied mechanically. The final prompt MUST describe the request as it plausibly
could have been given before the solution existed. It must not narrate the gold
diff, reveal internal implementation choices discovered through hindsight, or
sound artificially vague merely to increase failure rate.

Review prompt realism explicitly:

1. Could a real maintainer, developer, or user plausibly have written this?
2. Does its level of detail match the selected prompt scenario?
3. Does it state every required public behavior without prescribing the gold
   implementation?
4. Would the task still make sense to a competent human seeing only the base
   repository?

If not, rewrite the prompt or reject the candidate.

Use one primary `prompt_style` that reflects the actual human-agent interaction:

1. `casual-chat` — a terse conversational ask such as “make this stop dropping
   the first item.”
2. `outcome-request` — a goal or invariant with implementation left to the
   agent.
3. `symptom-report` — observed incorrect behavior without complete reproduction
   steps.
4. `reproduction-report` — current behavior, expected behavior, steps, inputs,
   or environment details.
5. `failure-report` — a pasted test failure, compiler diagnostic, log, stack
   trace, or error message followed by a request to fix it.
6. `issue-form` — a structured bug or feature report using headings and fields.
7. `localized-request` — the request names or highlights a relevant file,
   function, subsystem, or code selection.
8. `acceptance-spec` — a checklist or precise public behavioral contract.
9. `implementation-request` — the developer intentionally requests a named API,
   mechanism, migration, or implementation direction.
10. `review-and-fix` — the developer asks the agent to inspect existing code,
    improve it, and correct defects within a bounded scope.
11. `follow-up` — a long-run turn that refines, corrects, or extends earlier
    work using the existing conversation and repository state.

`prompt_source` is separate from style. Recommended values include
`original-issue`, `pr-derived`, `reverse-spec`, `human-reconstructed`, and
`composite`. It records where the task came from; `prompt_style` records how the
human request is expressed.

Use one `spec_level`:

- `minimal` — a short but still fair goal or invariant;
- `symptom-led` — the symptom or reproduction establishes the intended fix;
- `behavioral` — important public acceptance behavior is stated;
- `full-spec` — public APIs, formats, errors, edge cases, and compatibility are
  explicitly pinned where the real task requires them.

Short informal prompts have the strictest candidate-selection bar. They are
appropriate only when the correct behavior is unambiguous from the reported
symptom plus repository conventions. Features that pin API names, wire formats,
error codes, or exact output require those public requirements in the prompt.

Do not add irrelevant detail merely to make every case look like a full
specification. Do not remove required detail merely to make a case look harder.

### Research basis

This taxonomy combines traditional project requests with modern human-to-agent
chat. Real GitHub issue forms commonly collect current behavior, expected
behavior, reproduction steps, environment, and extra context. Coding-assistant
guidance and examples cover direct implementation, fixing errors, improving or
refactoring selected code, writing tests, referencing relevant files, and
iterative refinement. Empirical research on developer-ChatGPT conversations
finds code generation, issue resolution, how-to requests, and code review among
common inquiry categories, with initial tasks, contextual information,
iterative follow-ups, and prompt refinement in multi-turn use.

References:

- [SWE-bench real GitHub issue/PR tasks](https://proceedings.iclr.cc/paper_files/paper/2024/hash/edac78c3e300629acfe6cbe9ca88fb84-Abstract-Conference.html)
- [GitHub issue-form bug-report structure](https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
- [GitHub Copilot Chat prompt patterns](https://docs.github.com/en/copilot/how-tos/chat-with-copilot/get-started-with-chat-in-your-ide)
- [GitHub guidance on context and iterative prompting](https://docs.github.com/en/copilot/concepts/prompting/prompt-engineering)
- [Empirical study of developer-ChatGPT conversations](https://arxiv.org/abs/2403.10468)

## 7. Enforce the derivability rule

Every validation assertion MUST be derivable from the instruction, public
project behavior, and repository conventions visible to the agent.

Tests may be visible, hidden, or mixed according to the realistic scenario and
verification needs. Hidden requirements are never permitted.

Reject or repair a case when validation requires:

- an unstated public API name or signature;
- exact message prose not quoted or otherwise specified;
- an internal symbol, algorithm, or file layout chosen only by the gold author;
- the same code structure as the gold patch;
- behavior contradicting the prompt or the checked-out repository;
- knowledge available only from the hidden test or upstream solution.

For every assertion, ask:

1. What observable behavior does this assertion enforce?
2. Where can a competent human derive that requirement?
3. Would a different correct implementation also pass?

If question 2 or 3 has no defensible answer, change the prompt, narrow the
validation, or reject the case. Never weaken legitimate behavioral validation
solely because a model failed it.

## 8. Construct an objective validation contract

Validation SHOULD combine:

- fail-to-pass tests for the requested behavior;
- pass-to-pass regression coverage for adjacent existing behavior;
- a cheap build, type, lint, or syntax check where appropriate.

Validation MUST be:

- deterministic and repeatable;
- selective enough for the campaign budget;
- independent of internet access during test execution;
- based on observable behavior rather than gold implementation shape;
- strong enough to reject partial fixes and obvious overfitting;
- compatible with the exact base and target branch.

Set `test_visibility` case by case:

- `visible` — the failing test, assertion, or equivalent executable reproduction
  is part of the repository or request the agent receives;
- `hidden` — verification remains protected and the prompt independently states
  or implies everything it checks;
- `mixed` — the agent receives a visible reproduction or regression signal and
  protected tests verify additional derivable behavior.

Use visible verification when that is how the real developer interaction would
occur, for example “fix this failing test” or a pasted reproduction. Use hidden
verification when it prevents test rewriting or checks fair generalization.
Visibility is a verification choice, not a difficulty control.

Performance cases require special care. Prefer deterministic invariants such as
bounded work, allocation counts, cancellation, or algorithmic behavior. Raw
wall-clock thresholds are acceptable only with demonstrated stability and
meaningful margin in the benchmark environment.

## 9. Seal the solution from the agent

During the scored phase:

- the repository object store MUST contain only the required base history;
- the upstream remote MUST be removed;
- gold source and any tests classified as hidden MUST be unavailable;
- network access MUST be default-deny except for required model control-plane
  hosts;
- provider-native web search and unrelated plugins MUST be disabled;
- setup output, fixture names, comments, and instructions MUST not expose the
  solution.

Validation may restore network access only after the agent finishes, fetch the
gold commit, and restore protected validator copies. Agent edits to validation
tests must not manufacture a passing verdict.

After a client run, audit raw traces for `/case` reads, upstream re-fetches, web
search, mirrors, or other solution access. A leaked pass is invalid.

## 10. Prove fail-to-pass before the requested client run

Every case MUST pass both proof legs in the agent image:

1. Run setup at base and confirm objective validation fails for the intended
   missing behavior.
2. Apply only the gold production-source diff, excluding validation test paths, and
   confirm validation passes.

Also confirm that setup itself succeeds, the failure is relevant rather than
incidental, quality checks are meaningful, and the proof uses the same image
and architecture as the scored campaign.

A case that fails either proof leg does not enter the requested client run.

## 11. Run, audit, and finalize on the requested client

Once mechanically proven, every case in the harnessing request MUST be run
against the specified provider/model configuration. Use the normal sealed
environment and audit the complete trace and resulting patch, not only the exit
code.

Classify each result as one of:

- correct solution;
- legitimate incorrect, partial, or overfitted model failure;
- legitimate model timeout or resource exhaustion;
- unfair prompt/validation mismatch;
- infrastructure or provider failure;
- nondeterministic or invalid case;
- leakage or likely contamination.

Only correct passes and legitimate model failures are final model outcomes.
Infrastructure failures, unfair contracts, leakage, and invalid tests are
invalid runs and MUST be repaired or excluded before results are published.

Use the following repair loop:

1. If the prompt and validation are fair and execution is clean, finalize the
   result as a correct pass, partial/incorrect model failure, or timeout caused
   by the model itself.
2. If validation contains an underivable requirement, repair the prompt
   or narrow the invalid assertion without weakening legitimate behavior.
3. If setup, validation, sealing, provider execution, or infrastructure is at
   fault, repair that layer.
4. If the agent accessed the solution, discard the contaminated run and close
   the leak.
5. After any case or harness repair, repeat mechanical proof and rerun the same
   requested client/model before finalizing.

Do not modify a fair case merely to turn a pass into a failure or a failure into
a pass.

A single pass does not make a case bad, and a single failure does not make a
case good. When a frontier model solves a candidate quickly and completely, the
case may remain in the balanced corpus but is lower priority for the hard tier.
When repeated runs are requested, keep the prompt and environment fixed and
report the run count rather than selecting only a favorable outcome.

Finalization MUST record:

- exact case or sequence identifier and version-relevant changes;
- requested provider, model, run configuration, and environment;
- base and gold SHAs and mechanical proof status;
- objective validation result and meaningful quality failures;
- audit classification and evidence for that classification;
- leakage, infrastructure, nondeterminism, or contamination findings;
- attempts rerun after repairs, without hiding superseded invalid runs;
- tokens, cost, latency, and remaining limitations when available.

## 12. Finalize, admit, or reject

A candidate MUST remain outside the discoverable benchmark list while it is
being reconstructed, mechanically proven, or repaired. Keep drafts in
`cases/_specs/` or another non-discovered working location. Run targeted proof
and client commands against that candidate path.

Move a one-shot case under `cases/dev/oneshot/`, or a sequence under
`cases/dev/longrun/`, only after the requested client/model result has been
audited and finalized. A candidate with an unresolved fairness, provenance,
validation, infrastructure, leakage, or nondeterminism defect is not part of
the benchmark list.

Admit a case only when all of the following are true:

- provenance is credible and recorded;
- freshness and contamination risk are recorded;
- the prompt is realistic and every validation requirement is derivable;
- base-to-gold proof passes;
- validation is deterministic, selective, and implementation-independent;
- the solution remains sealed during the scored phase;
- the requested client/model has been run and the result has been audited;
- every invalid run discovered during auditing was repaired and rerun, or the
  case was rejected with the blocker recorded;
- the case adds useful coverage to the intended corpus or tier.

An admitted case MUST retain difficulty, task type, failure modes, prompt source/style,
specification level, test visibility, capability tags, provenance, test paths,
and known client-run history. Reject candidates that cannot satisfy the contract
without inventing requirements or matching private gold implementation choices.

## 13. Maintain the corpus

Case quality is not permanent. Periodically:

- refresh the post-cutoff candidate window;
- recheck upstream SHAs, branches, and test reproducibility;
- audit language, task-type, capability, prompt-style, and difficulty balance;
- separate infrastructure regressions from model regressions;
- retire or re-tier cases that no longer discriminate at the intended level;
- preserve valid easier cases when they still serve the balanced corpus;
- rerun leak audits whenever providers, images, network policy, or setup changes.

Existing mechanically valid cases may remain in the balanced corpus even when
they predate this document or are now easy for frontier models. Backfill their
classification tags by reviewing the actual prompt and validation before they
are included in the next audited list or campaign; this metadata migration does
not by itself require renaming identifiers or changing prompts. When an existing
case is materially edited, rerun, or moved into a new published tier, bring its
full provenance and audit record up to the current protocol.

Do not silently rewrite a case after results have been published. Record material
prompt, validation, base, gold, or environment changes so results from different
case versions are not treated as directly comparable.

# One-Shot Real-Commit Cases

One-shot cases test one autonomous engineering task against one objective
validation contract. Case selection and admission MUST follow the shared
[Real-Commit Harnessing Protocol](HARNESS.md).

This document defines the one-shot-specific layout, construction, proof, and run
procedure.

## Case model

A one-shot case starts from the repository immediately before a real merged
change. The agent receives one instruction and works independently in an
isolated workspace. After it stops, the harness installs the gold test paths and
runs objective validation.

The gold commit is a behavioral reference, not an exact patch target. Alternative
correct implementations must be accepted by the tests.

## Layout

Cases live under:

```text
cases/dev/oneshot/<language>/<case_name>/
├── case.yaml
├── setup.sh
├── quality.sh
├── validate.sh
└── fixtures/          # optional
```

Discovery is based on `case.yaml`. Use `templates/case.yaml` as a structural
starting point, then add the required real-commit metadata.

Choose a short `<case_name>` that describes the project and behavior, for
example `monolog_trace_limit`. Do not prefix it with `dev`, `oneshot`, the
language, a batch number, a model name, or an observed result; the directory
hierarchy and metadata already carry those dimensions. Follow the complete
identity and metadata contract in `HARNESS.md`.

The manifest records at least:

```yaml
id: rust_example_behavior
name: Example behavior fix
category: dev
difficulty: complex
meta:
  repo: https://github.com/owner/repository
  pr_url: https://github.com/owner/repository/pull/123
  issue_url: https://github.com/owner/repository/issues/100 # when applicable
  task_type: bug-fix
  failure_modes: [wrong-result]
  prompt_source: original-issue
  prompt_style: reproduction-report
  spec_level: symptom-led
  test_visibility: mixed
  capability_tags: [debugging, parser, regression]
  target_branch: main
  base_sha: 0000000000000000000000000000000000000000
  gold_sha: 1111111111111111111111111111111111111111
  test_paths:
    - tests/example.rs
system_prompt: |
  You are an autonomous software engineer working in an existing repository at the current directory.
  Resolve the requested task completely, as the project's maintainers would. When done, stop.
instruction: |
  Describe the realistic task and its complete public behavior contract.
```

Metadata is read by tooling and humans even when the runner does not use every
field. Keep it accurate.

## Construction workflow

### 1. Select and audit the merged change

Apply all candidate, freshness, provenance, project-quality, balance, and
derivability gates from `HARNESS.md`.

For one-shot cases, additionally confirm:

- the base SHA is the gold merge commit's intended pre-change state;
- the production diff can be isolated from test changes;
- the validation test paths contain both the new behavior and useful regressions;
- unrelated commits did not inject impossible assertions into the selected test
  files between base and gold.

### 2. Reconstruct the task as it could have arrived

The default reverse-spec workflow is:

```bash
scripts/reverse_spec.sh <repo_url> <gold_sha> [out.md]
```

It emits a candidate task prompt and clarified specification. Reverse-spec is
one input, not an instruction to paraphrase the gold diff.

Reconstruct the task from the best available combination of the original issue,
PR description, review discussion, gold tests, and production solution. The
solution may be inspected to understand the flow and recover the intended
behavior, but implementation details learned from it must not leak into the
prompt unless they are genuine public requirements.

Drafts belong in `cases/_specs/` or another non-discovered candidate location.
Do not add a candidate to `cases/dev/oneshot/` merely because its manifest and
scripts have been written.

The final instruction may instead use an original issue, a short human prompt,
a support ticket, an acceptance story, or another realistic style described in
`HARNESS.md`. Record the source/style in metadata.

The instruction is curated against every validation assertion. Use a short prompt
only when any competent fix for the stated invariant will pass. Include exact
public API names, formats, codes, compatibility rules, or output behavior when
the tests pin them. The result must sound like a plausible real request that
could have existed before the patch. Never expose gold implementation details.

### 3. Write `setup.sh`

`setup.sh` is bash and is responsible for the complete environment:

1. Initialize an empty Git repository in the workspace.
2. Fetch only `BASE_SHA` with shallow history.
3. Check it out on the working branch.
4. Remove the upstream remote.
5. Install every dependency needed by the agent and validation.
6. Warm expensive builds when practical.

Use `$CASE_DIR` for case-owned fixtures. The scored agent phase must not require
package downloads or upstream access.

Typical checkout shape:

```bash
git init -q .
git remote add origin "$REPO_URL"
git fetch -q --depth 1 origin "$BASE_SHA"
git checkout -q "$BASE_SHA"
git checkout -q -B main
git remote remove origin
```

The gold commit must not be present in the object store after setup.

### 4. Write `quality.sh`

`quality.sh` is bash and performs cheap objective checks appropriate to the
project, such as compilation, syntax, types, or focused linting.

Quality checks should detect malformed or non-building solutions without
duplicating the complete validation suite. They must be deterministic and
reasonably bounded.

### 5. Write `validate.sh`

`validate.sh` is bash and returns non-zero on failure. It should:

1. Re-add the upstream remote after the scored phase.
2. Fetch the exact gold SHA.
3. Check out the recorded protected gold test paths, overwriting agent edits
   where independent validation is required.
4. Run focused fail-to-pass and regression tests.

Do not check out gold production source during normal validation. Do not accept
agent-authored replacements for protected validation tests as evidence of
correctness.

The agent may receive a visible failing test, an executable reproduction, or no
test at all depending on `test_visibility`. Protected gold validation remains
allowed in every mode, but it may only assert requirements derivable from the
prompt and visible repository context.

The validation command must be selective, deterministic, network-independent,
and broad enough to reject partial fixes.

### 6. Prove both legs

Run:

```bash
scripts/verify_case.sh <candidate_dir>
```

The verifier must prove:

- setup succeeds;
- validation fails at base for the intended reason;
- the first-parent gold production diff applies with test paths excluded;
- validation passes after applying that source diff.

A case does not proceed to the requested client run until this proof passes in
the current agent image.

### 7. Run, audit, and finalize the requested client

Every case in the harnessing request must now run against the specified
client/model using the normal sealed Docker campaign. Audit:

- the full agent trace and tool use;
- the resulting source diff;
- validation and quality logs;
- upstream, web, `/case`, or other solution access;
- whether a failure is a real capability failure, an unfair contract, or
  infrastructure.

Use the classification and repair loop in `HARNESS.md`. If the case or harness
is defective, repair it, repeat fail-to-pass proof, and rerun the requested
client/model. Do not modify a fair case solely to force a particular model to
pass or fail. The case is finalized only after the run has a trustworthy pass or
legitimate model-failure classification.

Only after that finalization may the case be moved into the discoverable
`cases/dev/oneshot/` list.

## Sealed execution

Before a campaign, run the repository preflight documented in `USAGE.md`:

```bash
.venv/bin/python scripts/bench_selftest.py
.venv/bin/python scripts/sync_system_prompt.py --check
.venv/bin/python scripts/seal_probe.py
```

Run one-shot development cases with `OCTOBENCH_SEAL_NETWORK=1`, Docker execution,
the checked-in agent image, and a pinned provider/model run matrix. Exact commands
for the supported providers live in `USAGE.md`.

Afterward, audit traces before publishing results:

```bash
.venv/bin/python scripts/audit_web.py <result-directory> [...]
```

## Admission checklist

- [ ] Real merged human-provenance change from a suitable project.
- [ ] Freshness and contamination risk assessed.
- [ ] Production source and deterministic tests both changed.
- [ ] Base, gold, target branch, PR, issue, and test paths verified.
- [ ] Prompt style is realistic and recorded.
- [ ] Every validation assertion passes the derivability rule.
- [ ] Difficulty, task type, failure modes, prompt style, specification level,
      test visibility, and capability tags are assigned consistently.
- [ ] Alternative correct implementations can pass.
- [ ] Setup contains no gold history and removes upstream access.
- [ ] Dependencies are fully prepared before the sealed phase.
- [ ] Base validation fails for the intended behavior.
- [ ] Gold production source passes validation.
- [ ] Quality and validation commands are selective and deterministic.
- [ ] Requested client/model run is classified and trace-audited.
- [ ] Any harness repair was re-proven and rerun on that same client/model.
- [ ] Final outcome and superseded invalid attempts are reported.
- [ ] The case improves corpus balance or the intended difficulty tier.

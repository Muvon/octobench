# Octobench: Agent Onboarding

This file is the entrypoint for contributors and agents.

## Start Here
- Read `docs/USAGE.md` for how to run benchmarks.
- Read `docs/ARCHITECTURE.md` for core concepts and flow.
- Read `docs/EXTENDING.md` to add new cases or tools.
- Read `docs/PROVIDER_INTERFACE.md` before implementing/changing providers.

## Repo Layout
- `cases/`: benchmark cases in `cases/<segment>/<sub_or_lang>/<case_name>/` with scripts + fixtures
- `configs/`: model registry, run matrices, and octomind config
- `providers/`: provider implementations (`claude`, `codex`, `octomind`) with shared interface; each runs its framework at its out-of-the-box default
- `runners/`: `executor.py` (Host/Docker execution), `cli_runner.py` (judge invocation)
- `docker/`: `Dockerfile.agent` (agent image for `--executor docker`), `Dockerfile.swebench` (per-instance derived image), `Dockerfile.tau2` + `tau2_bridge.py` (tau2-bench solo image + shell bridge)
- `cli/`: `main.py` (local-case runner), `swebench.py` (SWE-bench-Live runner), `bench.py` (unified multi-domain benchmark runner)
- `benchmarks/`: config-driven benchmark adapters (`qa`, `docker_task`, `swebench_live`) + matchers/constraint engine (`verify.py`); `ifbench_vendor/` (vendored allenai IFBench checkers); configs in `configs/benchmarks/*.yaml`
- `judges/`: judge prompt + parsing
- `scoring/`: metrics + aggregation; `scripts/summary.py`: comparison table
- `results/`, `results-swebench/`: output JSON for runs

## How It Works (Short)
1. For each case + provider + benchmark model, create an isolated workspace.
2. Copy scripts into workspace.
3. Run `setup.sh` (responsible for full setup), take baseline snapshot, then the tool, then `quality.sh` and `validate.sh`.
4. Feed tool output + script logs into the judge.
5. Compute scores and write JSON.

## Rules
- `setup.sh`, `quality.sh`, `validate.sh` are bash only.
- Use `$CASE_DIR` inside scripts to reference case assets (e.g., `$CASE_DIR/fixtures`).
- Evidence is captured via before/after snapshots and diffed for the judge.
- `validate.sh` non-zero exit is a hard fail.
- Judge prompt is hardcoded in `judges/prompts.py`.

## Quick Run
```bash
python3 -m cli.main run --cases cases --providers codex,octomind --verbosity normal
```

## Add a Case
- Copy `templates/case.yaml` and create a new case folder.
- Put fixtures under `fixtures/`.
- Add scripts as needed.

## Real-Commit Case Harvesting (cases/dev)

`cases/dev/<lang>/<case>/` cases are reverse-engineered from REAL merged PRs in
trusted open-source repos. The pipeline, end to end:

1. **Mine candidates.** Search merged PRs in respected, actively-maintained
   repos (high review bar, real CI). Hard criteria:
   - **Recency beats everything: merged AFTER the newest model's training
     cutoff** (contamination control — the fix must be unseen; prefer the most
     recent mergeable window and refresh the case set as cutoffs move).
   - Human-authored; not a revert/docs/refactor/CI-only change.
   - Diff touches BOTH production source and tests; tests deterministic, no
     network at test time, runnable selectively (single file / filter).
   - Variety on two axes: scenario (simple edit / crash fix / bug fix /
     feature) and granularity (~1-line to a few hundred lines), spread across
     languages/build systems.
   - Toolchain must exist in `docker/Dockerfile.agent` (or extend it).
2. **Reverse the task.** `scripts/reverse_spec.sh <repo_url> <gold_sha> [out.md]`
   runs the tap agent `developer:reverse-spec` on the gold commit and emits the
   as-it-arrived Task Prompt + Clarified Spec. Draft specs live in
   `cases/_specs/` (gitignored — working material, not repo content).
   Two alternative prompt scenarios exist alongside the reverse-spec default:
   `prompt_source: original-issue` (the issue text verbatim, trimmed of
   fix-leaking sections) and `prompt_source: human-prompt` (a 1-3 sentence
   casual developer ask). Human-prompt cases carry the strictest selection
   bar: the correct behavior must be unambiguous from the symptom plus the
   repo's existing conventions — crash fixes and obviously-wrong-behavior
   only, never features, and the prompt should state the *invariant* (what
   must never happen), not just the repro, when tests cover failure modes
   beyond the literal reproduction.
3. **Curate the instruction** (`case.yaml` `instruction:`) by the
   **derivability rule**: everything the hidden tests assert must be derivable
   from the instruction alone.
   - Bug/crash fix where any correct fix passes → the short informal prompt.
   - Feature whose tests pin public API names, wire formats, error codes, or
     exact output → prompt + the pinning requirements from the Clarified Spec.
   - A test asserting an internal name/pick no spec could state = taste-graded
     → reject the case (or drop that test file from `validate.sh`).
   - Issue-driven cases obey the SAME rule against the issue text: read every
     held-out assertion and check it is derivable from the issue. Exact
     error-message PROSE the issue never quotes is the classic trap (codes and
     exception types are fine — they're API surface); an otherwise-perfect fix
     fails on wording (observed: agent matched the maintainer's error id but
     not the message string). Verify the string-level assertions, not just
     which codes/types a test mentions.
4. **Case mechanics** (leak hygiene, learned the hard way on SWE-bench-Live):
   - `setup.sh`: `git init` + `git fetch --depth 1 origin BASE_SHA` (single
     reachable commit — gold is not in the object store), branch, `git remote
     remove origin`, then full env prep (installs into `/opt/venv`, vendor/,
     node_modules, warm cargo/cmake builds).
   - `validate.sh`: re-adds origin, fetches GOLD_SHA **at verify time**, checks
     out ONLY the gold test paths (agent never sees them; agent edits to tests
     are overwritten), runs those tests. The gold test file usually carries old
     + new tests, so one run covers fail-to-pass and regressions.
   - `quality.sh`: cheap objective build/lint only.
   - `case.yaml` `meta:` records repo/base_sha/gold_sha/test_paths plus
     provenance links — `pr_url` always, `issue_url` when the case derives
     from a reported issue (harness ignores meta; tooling and humans read it).
5. **Prove fail-to-pass before benching.** `scripts/verify_case.sh <case_dir>`
   (agent image): setup → validate must FAIL at base → apply gold source (first-
   parent diff, test paths excluded) → validate must PASS. A case that fails
   either leg does not ship.
6. **Audit after runs**: grep provider traces for `/case` reads or upstream
   re-fetches — the two remaining leak paths are visible in traces.

## Add a Tool
- Add `providers/<name>.py` implementing `Provider.run_task(...)`.
- Register it in `providers/factory.py`.
- Add model mapping under `configs/models.yaml -> models.<benchmark>.providers.<name>`.

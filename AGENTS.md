# Octobench: Agent Onboarding

This file is the entrypoint for contributors and agents.

## Start Here
- Read `docs/USAGE.md` for how to run benchmarks.
- Read `docs/ARCHITECTURE.md` for core concepts and flow.
- Read `docs/EXTENDING.md` to add new cases or tools.
- Read `docs/PROVIDER_INTERFACE.md` before implementing/changing providers.
- Read `docs/HARNESS.md` before mining, constructing, running, auditing, or
  finalizing real-commit development cases for a requested client/model.
- Read `docs/ONESHOT.md` for one-shot cases and `docs/LONGRUN.md` for multi-turn
  sequences.

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

## Real-Commit Development Cases (`cases/dev`)

The authoritative case-selection and acceptance rules are in
`docs/HARNESS.md`. Format-specific construction rules are split into:

- `docs/ONESHOT.md` — `cases/dev/oneshot/<lang>/<case>/`, one instruction and
  one validation contract, run by `cli.main`.
- `docs/LONGRUN.md` — `cases/dev/longrun/<lang>/<repo>/`, multiple related
  turns in one persistent session, run by `cli.longrun`.

Discovery is by manifest filename (`case.yaml` or `sequence.yaml`), so both
formats live under `cases/dev` without interference.

Non-negotiable invariants:

- Use credible, recent, human-provenance merged work from maintained projects.
- Every validation assertion must be derivable from the instruction and visible
  repository conventions. Tests may be visible, hidden, or mixed; hidden
  requirements are forbidden.
- Tag every new one-shot task and long-run turn by difficulty, task type,
  failure modes, prompt style/source, specification level, test visibility, and
  capability demands.
- Gold is a behavioral reference, not an exact patch target.
- Prove fail-at-base and pass-with-gold-source before the requested client run.
- Keep gold source, protected tests, and upstream solution access sealed from
  the agent.
- Classify infrastructure, unfairness, leakage, and nondeterminism separately
  from legitimate model failures.
- After any harness repair, repeat proof and rerun the same requested
  client/model; finalize only a trustworthy pass or legitimate model failure.

## Add a Tool
- Add `providers/<name>.py` implementing `Provider.run_task(...)`.
- Register it in `providers/factory.py`.
- Add model mapping under `configs/models.yaml -> models.<benchmark>.providers.<name>`.

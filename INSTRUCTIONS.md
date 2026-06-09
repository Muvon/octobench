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
- `docker/`: `Dockerfile.agent` (agent image for `--executor docker`), `Dockerfile.swebench` (per-instance derived image)
- `cli/`: `main.py` (runner), `swebench.py` (SWE-bench-Live single-instance runner)
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

## Add a Tool
- Add `providers/<name>.py` implementing `Provider.run_task(...)`.
- Register it in `providers/factory.py`.
- Add model mapping under `configs/models.yaml -> models.<benchmark>.providers.<name>`.

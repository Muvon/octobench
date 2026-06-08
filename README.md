# octobench

> **WIP Notice:** This project is actively under development and APIs/behavior may change without notice. Use at your own risk while we stabilize it.

Benchmark framework to compare **LLM tool + config + prompt** setups across a shared set of cases.

Contribution guide: see `CONTRIBUTING.md` (focused on adding new cases).

## Key ideas
- **Cases** define prompts and scripts.
- **Providers** are Python implementations that run tools and return normalized telemetry.
- **Judge** is an LLM prompt with strict JSON output.
- **setup.sh / quality.sh / validate.sh** are bash scripts whose logs are fed to the judge.

## Quick start
1. Create a venv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run all cases using default run matrix (`configs/run-matrix.yaml`):

```bash
python3 -m cli.main run --cases cases
```

Override with another run-matrix config:

```bash
python3 -m cli.main run --cases cases --config configs/run-matrix.yaml
```

Results land in `results/` as JSON.
`--verbosity` is optional (default: `normal`).

## Development checks
Install and enable pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

CI runs the same `pre-commit` checks on every pull request, plus a Python compile check.

## Cases
Each case is a folder with a `case.yaml` plus optional scripts:

```
cases/<segment>/<sub_or_lang>/<case_name>/
  case.yaml
  setup.sh
  quality.sh
  validate.sh
  fixtures/
```

Example:

```
cases/dev/rust/unexpected_closing_delimiter_fix/
```

Script behavior:
- `setup.sh`: setup workspace/fixtures (always runs).
- `quality.sh`: run checks (lint/tests). Output is fed to the judge.
- `validate.sh`: run correctness checks. Output is fed to the judge. Any non-zero exit hard-fails the case.

Scripts run in the workspace. Use `$CASE_DIR` to access case assets (e.g., `$CASE_DIR/fixtures`).

## Fairness model
Each framework runs **at its out-of-the-box default** — no benchmark-tuned prompts,
roles, or configs that would stack the deck:
- **claude**: `claude -p --model <model> --dangerously-skip-permissions`
- **codex**: `codex exec -m <model> -s workspace-write`
- **octomind**: `octomind run developer:general -m <model>` — octomind's stock
  coding agent. Its config (`configs/octomind/octomind.toml`) is the upstream
  octomind baseline (`config-templates/default.toml`) left **untouched** and
  extended with only a `judge` role (see below). The lone deviation is
  `[capabilities] websearch = "brave"`, which swaps a default web-search provider
  whose npm package is unpublished — it activates lazily and never fires on the
  coding cases.

The judge is the only intentional customization, and it is a separate role that
cannot influence how the frameworks-under-test run.

## Providers
Provider implementations live in:
- `providers/claude.py`
- `providers/codex.py`
- `providers/octomind.py`
- `providers/base.py`
- `providers/factory.py`

Model registry:
- `configs/models.yaml` defines benchmark model keys, pricing (per-1M), and provider-specific mappings.
- Default run selection comes from `configs/run-matrix.yaml`.
- You can still filter with `--providers`/`--models` (cross-product mode).

## Add new provider
1. Add provider implementation in `providers/<name>.py` implementing `Provider`.
2. Register it in `providers/factory.py`.
3. Add provider mapping under each benchmark model in `configs/models.yaml`.
4. Follow `docs/PROVIDER_INTERFACE.md` for token semantics and evidence consistency.

## Add new benchmark model
1. Add a new key under `configs/models.yaml`.
2. Add `pricing` (per-1M input/cached_input/output).
3. Add `providers` mapping entries for each provider you use.

## Judge
The judge prompt is hardcoded in `judges/prompts.py` and expects JSON output.
The judge runs as an Octomind **role** appended to the baseline config:
- `OCTOMIND_CONFIG_PATH={repo_root}/configs/octomind/octomind.toml`
- Command: `octomind run judge -m <judge_model> --format=jsonl`
- Default judge model: `octohub:minimax`; override with `OCTOBENCH_JUDGE_MODEL`

The `judge` role has no tools and emits strict JSON, so it is isolated from the
benchmarked runs. `configs/octomind/octomind.toml` is octomind's upstream
`config-templates/default.toml` kept verbatim, with only the `judge` role (and the
`websearch = "brave"` capability override) added at the end.

## Scoring
Scoring is globally configurable via config files. The framework collects:
- judge score (0-100)
- latency
- token usage (if the CLI emits it and you configure regex)
- cost (from `configs/models.yaml`, required)
- script logs (setup/quality/validate)

Final score is computed using global scoring weights.
Validation failures apply a configurable penalty (`validation_fail_penalty`).

## Verbosity
- `--verbosity quiet`: only final output line
- `--verbosity normal`: progress per case/provider
- `--verbosity debug`: includes provider/benchmark model mapping details

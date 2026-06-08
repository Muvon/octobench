# Usage

## Quick run (no install)
```bash
python3 -m cli.main run --cases cases --verbosity normal
```

This writes a JSON report under `results/<timestamp>.json`.

## CLI arguments
```bash
python3 -m cli.main run \
  --cases cases \
  --config configs/run-matrix.yaml \
  --out results \
  --scoring configs/scoring.yaml \
  --efficiency configs/efficiency.yaml \
  --verbosity normal
```

Required:
- `--cases`: Path to cases directory (e.g., `cases`)

Optional:
- `--config`: Run-matrix YAML with explicit provider/model pairs (default: `configs/run-matrix.yaml`)
- `--providers`: Comma-separated provider names for cross-product mode
- `--models`: Comma-separated benchmark model keys for cross-product mode
- `--out`: Output directory base name (default: `results`)
- `--scoring`: Path to scoring config (default: `configs/scoring.yaml`)
- `--efficiency`: Path to efficiency config (default: `configs/efficiency.yaml`)
- `--verbosity`: quiet, normal, or debug

Run-matrix example:
```yaml
runs:
  - provider: codex
    model: gpt-5.2-codex
  - provider: octomind
    model: minimax-m2.5
```

Command:
```bash
python3 -m cli.main run --cases cases --config configs/run-matrix.yaml
```

## What happens in a run
For each case and selected run target (provider + benchmark model pair):
1. Creates an isolated workspace.
2. Copies scripts to workspace.
3. Runs `setup.sh` (responsible for full setup).
4. Captures a baseline snapshot for evidence.
5. Sends the case prompt to the selected provider implementation.
6. Captures a post-run snapshot + diff evidence.
7. Runs `quality.sh` and `validate.sh`.
8. Sends tool output + script logs + evidence to the judge.
9. Computes scores and writes JSON.

## Octomind integration
- Provider runs octomind's stock coding agent: `octomind run developer:general -m <model>`
- Judge runs as a dedicated role: `octomind run judge -m <model>`
  (default `octohub:minimax`, override with `OCTOBENCH_JUDGE_MODEL`)
- Both use the pinned config via env:
  - `OCTOMIND_CONFIG_PATH={repo_root}/configs/octomind/octomind.toml`
- That config is octomind's upstream `config-templates/default.toml` kept untouched,
  extended only with the `judge` role and a `websearch = "brave"` capability override.

## Key outputs
Each result record contains:
- tool output, logs, exit code, latency
- token usage (if configured)
- cost (from `configs/models.yaml`, per-1M tokens, required)
- judge output (score + issues)
- scoring (final score, efficiency, validation failure)

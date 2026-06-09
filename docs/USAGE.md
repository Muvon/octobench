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
- `--executor`: `host` (default, local subprocesses) or `docker` (per-case container)
- `--image`: Docker image for `--executor docker` (default `octobench-agent:latest`)

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

## Docker execution
Build the agent image once, then pass `--executor docker`:

```bash
docker build -f docker/Dockerfile.agent -t octobench-agent:latest docker
python3 -m cli.main run --cases cases --executor docker
```

Each case runs in its own container (`runners/executor.py: DockerExecutor`). Host
auth is injected at `docker run`: API-key env vars are forwarded by name, the
octomind config is mounted at `/cfg/octomind.toml`, `~/.codex/auth.json` is mounted
read-only, and `IS_SANDBOX=1` lets claude run headless as root. The workspace is a
host dir bind-mounted at `/workspace`, so before/after snapshots still happen on the
host. Agents are pinned Linux binaries baked into the image (no compiling).

## SWE-bench-Live
Run one real GitHub issue end-to-end (agent fix + the instance's own tests as the
verdict):

```bash
python3 -m cli.swebench --split lite --config configs/run-matrix.swebench.yaml
python3 -m cli.swebench --instance jupyterlab__jupyter-ai-1022   # specific instance
python3 scripts/summary.py results-swebench
```

Flow: fetch the instance from the `SWE-bench-Live/SWE-bench-Live` HF dataset → layer
agent binaries onto its prebuilt image (`docker/Dockerfile.swebench`) → run the agent
repo-in-image at `/testbed` → reset to `base_commit`, apply the test patch, run
`test_cmds`, and check `FAIL_TO_PASS`/`PASS_TO_PASS`. Instance images are x86_64
(emulated on Apple Silicon). Results carry a `swebench.resolved` verdict.

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

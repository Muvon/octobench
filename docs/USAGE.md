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

## Multi-domain benchmarks (`cli.bench`)
The unified runner runs any benchmark in `configs/benchmarks/*.yaml` across the agent
SETUPS (provider + model + executor) and writes results to `results-bench/<timestamp>/`.
It reuses the same executor, judge, and scoring as the case/SWE-bench runners, so
results are directly comparable.

List the catalog (domain, engine, fit, readiness):
```bash
python3 -m cli.bench --list
```

Run a benchmark (each example is verified working):
```bash
# objective MCQ (knowledge) via the local claude login — no API key needed
python3 -m cli.bench --benchmark mmlu --limit 5 --providers claude --models claude-sonnet-4

# instruction-following: programmatic constraint check, no judge required
python3 -m cli.bench --benchmark ifeval --limit 5 --providers claude --models claude-sonnet-4 --no-judge

# via octomind over the octohub gateway (export the gateway URL + key first)
export OCTOHUB_API_URL=https://octohub.muvon.ltd      # OCTOHUB_API_KEY must also be set
python3 -m cli.bench --benchmark mmlu        --limit 5 --providers octomind --models minimax-m3
python3 -m cli.bench --benchmark financebench --limit 3 --providers octomind --models minimax-m3   # judge-scored

# coding: real GitHub issue, repo-in-image (Docker)
python3 -m cli.bench --benchmark swebench_live --split lite --limit 1 --providers octomind --models minimax-m3

python3 scripts/summary.py results-bench    # comparison table (latest run)
```

Flags (superset of `cli.main`):
- `--benchmark NAME|path` — config under `configs/benchmarks/` (or a `.yaml` path)
- `--list` — print the catalog and exit
- `--limit N`, `--split S`, `--instance ID` — instance selection
- `--providers` / `--models` — cross-product setup selection (or use `--config <run-matrix>`)
- `--no-judge` — skip the LLM judge; objective benches (`mcq`/`final_answer`/`constraint`)
  still score from their verdict (saves cost/time; the judge is only a secondary lens there)
- `--executor host|docker`, `--image`, `--scoring`, `--efficiency`, `--verbosity`,
  `--out` (default `results-bench`)

Provider/model pairing: each model key in `configs/models.yaml` maps to specific
providers — pair them correctly (`claude`+`claude-sonnet-4`, `codex`+`gpt-5.2-codex`,
`octomind`+`minimax-m3`). Cross-product only works for pairs that have a mapping;
otherwise use a run-matrix (e.g. `configs/run-matrix.bench.yaml`).

Engines & verdict:
- `qa` — single-turn. `mcq`/`final_answer`/`constraint` produce an OBJECTIVE,
  contamination-resistant verdict that drives `final_score` (100/0, like SWE-bench-Live);
  `judge_text` is graded by the LLM judge against a rubric.
- `docker_task` — env-required benches (CTF/CVE, terminal, FHIR, SQL...): run setup +
  agent + a verify command in a container and derive a programmatic pass/fail.
- `swebench_live` — real GitHub issues (wraps `cli.swebench`).

Readiness column in `--list`: **data** = runs now from Hugging Face / inline (needs a
model login/key); **needs-image** = needs the upstream Docker image (each config's
`notes` says how to wire it); **docker** = SWE-bench-Live per-instance images.

Auth: the `claude` provider uses your local claude login (no key). The `octomind`
provider AND the judge route through the octohub gateway, so set `OCTOHUB_API_URL` and
`OCTOHUB_API_KEY` in the RUN environment — note a non-interactive `ssh host 'cmd'` shell
does NOT inherit your interactive exports, so put them in the box's profile for remote
runs. Validate the whole framework offline (no network/API) with
`python3 scripts/bench_selftest.py`. Full catalog + how to add a benchmark:
`configs/benchmarks/README.md`.

Per-benchmark extras (host-side, only for the benches that need them):
- **`ifbench`** — the constraint checkers are vendored from allenai and need
  `pip install -r requirements.txt` (`nltk`/`emoji`/`syllapy`; nltk corpora download once
  on first use). These run in the `cli.bench` process on the host, not in the container.
- **`hle`** — `cais/hle` is gated: accept the terms on Hugging Face and set `HF_TOKEN`
  (public-gated read) in the run env; `benchmarks/hf.py` uses it host-side for the data
  load only (the token is never forwarded into the agent container).
- **`tau2_bench`** — build its image first:
  `docker build -f docker/Dockerfile.tau2 -t octobench-tau2:latest docker`; octomind needs
  `octomind_agent: developer:general` (shell-capable) to drive the `tau2` bridge.

## Octomind integration
- Provider runs a **task-appropriate** octomind agent (tested fairly per task type):
  - coding cases (local cases, SWE-bench, `docker_task`) → `developer:general`
  - non-coding `cli.bench` tasks (QA / instruction-following) → `assistant:general`
  - selected by `cli.bench` (engine default), overridable per benchmark with
    `octomind_agent: <tag>` in the config, or globally via the `OCTOMIND_AGENT` env var.
  - NOTE: the captured final answer is the agent's FULL message (octomind provider
    keeps full text for the verdict; only the judge-evidence trace is compacted).
- Provider runs octomind's stock coding agent: `octomind run <agent> -m <model>`
- Judge runs as a dedicated role: `octomind run judge -m <model>`
  (default `octohub:minimax`, override with `OCTOBENCH_JUDGE_MODEL`)
- Both use the pinned config via env:
  - `OCTOMIND_CONFIG_PATH={repo_root}/configs/octomind/octomind.toml`
- That config is octomind's upstream `config-templates/default.toml` (synced to the
  current template, which includes the `[supervisor]` control plane) kept untouched,
  extended only with the `judge` role and a `websearch = "brave"` capability override.
  To re-sync after an octomind upgrade: copy the current `config-templates/default.toml`,
  re-add those two edits, and validate with `scripts/bench_selftest.py` + an octomind smoke.

## Key outputs
Each result record contains:
- tool output, logs, exit code, latency
- token usage (if configured)
- cost (from `configs/models.yaml`, per-1M tokens, required)
- judge output (score + issues)
- scoring (final score, efficiency, validation failure)

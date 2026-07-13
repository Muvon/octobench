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

Compare a run at a glance:

```bash
python3 scripts/summary.py            # newest run under results/
python3 scripts/summary.py path/to/results.json
```

## Execution modes (host vs Docker)
`--executor` selects where each case runs:
- `host` (default): cases run as local subprocesses in a fresh workspace dir.
- `docker`: each case runs in its own container for a consistent, reproducible
  environment. Host auth is injected (never baked in): API-key env vars are
  forwarded by name (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OCTOHUB_API_KEY`, …)
  and `~/.codex/auth.json` is mounted read-only. `IS_SANDBOX=1` is set so claude
  runs headless as root.

Build the agent image once (pins prebuilt agent binaries — no compiling), then run:

```bash
docker build -f docker/Dockerfile.agent -t octobench-agent:latest docker
python3 -m cli.main run --cases cases --executor docker --image octobench-agent:latest
```

The image bundles `octomind`/`octofs`/`octocode` (static musl), `claude`, `codex`
(npm), plus a Rust toolchain and Python. See `docker/Dockerfile.agent`.

## SWE-bench-Live (real-world dataset)
Run a real, post-2024 GitHub issue (contamination-resistant) through the same
flow — agent fixes the repo, the instance's own tests are the objective verdict:

```bash
python3 -m cli.swebench --split lite --config configs/run-matrix.swebench.yaml
# or a specific instance:
python3 -m cli.swebench --instance jupyterlab__jupyter-ai-1022
python3 scripts/summary.py results-swebench   # shows the resolved (F2P/P2P) verdict
```

Instances are pulled from the `SWE-bench-Live/SWE-bench-Live` HF dataset. Each
instance's prebuilt image (DockerHub `starryzhang/…`, x86_64) is layered with the
agent binaries (`docker/Dockerfile.swebench`) and run repo-in-image at `/testbed`;
`validate` runs the instance's `test_cmds` and checks `FAIL_TO_PASS`/`PASS_TO_PASS`.
Note: instance images are x86_64, so on Apple Silicon they run under emulation.

## Multi-domain benchmarks (`cli.bench`)
SWE-bench-Live answers "which setup wins at coding". The unified bench runner
extends that to **every domain** — knowledge, math, instruction-following, health,
finance, cyber, science, data, marketing, legal, browser, computer-use,
orchestration — by turning credible, contamination-resistant benchmarks into
octobench cases. Each benchmark is a YAML config (`configs/benchmarks/*.yaml`) bound
to one of three adapter engines:

- **`qa`** — single-turn QA. Objective modes (`mcq` / `final_answer` / `constraint`)
  compute a deterministic verdict; `judge_text` uses the LLM judge against a rubric.
- **`docker_task`** — env-required benches: run setup + the agent + a verify command
  in a container, derive a programmatic pass/fail (generalizes SWE-bench-Live).
- **`swebench_live`** — the existing real-GitHub-issue flow, registered as an adapter.

```bash
python3 -m cli.bench --list                              # catalog across domains
# objective MCQ via the local claude login (no API key); --providers/--models pick the setup
python3 -m cli.bench --benchmark mmlu_pro --limit 5 --providers claude --models claude-sonnet-4
python3 -m cli.bench --benchmark aime25 --limit 10 --providers claude --models claude-sonnet-4   # math, post-cutoff
python3 -m cli.bench --benchmark ifeval --limit 10 --providers claude --models claude-sonnet-4 --no-judge

# via octomind over the octohub gateway (export the gateway URL + key first)
export OCTOHUB_API_URL=https://octohub.muvon.ltd         # OCTOHUB_API_KEY must also be set
python3 -m cli.bench --benchmark financebench --limit 5 --providers octomind --models minimax-m3
python3 -m cli.bench --benchmark swebench_live --split lite --limit 1 --providers octomind --models minimax-m3
python3 -m cli.bench --benchmark ctf_smoke --executor docker   # self-contained Docker proof
python3 scripts/summary.py results-bench                 # comparison table
```

Pick setups with `--providers/--models` (pair each model with a provider it maps to in
`configs/models.yaml`) or a run-matrix (`configs/run-matrix.bench.yaml`). `--no-judge`
skips the judge — objective benches still score from their verdict. The `octomind`
provider and the judge route through octohub, so set `OCTOHUB_API_URL`/`OCTOHUB_API_KEY`
in the run env; the `claude` provider uses your local claude login.
Benches marked **data** in `--list` run today from Hugging Face / inline data;
**needs-image** ones need their upstream Docker image (see each config's `notes`).
A few need host-side extras: `hle` is gated (set `HF_TOKEN`), `ifbench` uses the
vendored allenai checkers (from `requirements.txt`), and `tau2_bench` needs its image
(`docker build -f docker/Dockerfile.tau2 -t octobench-tau2:latest docker`) — see
`docs/USAGE.md` and `configs/benchmarks/README.md`.
The verdict is contamination-resistant when it's objective (`validate.sh`-style),
so the runner biases there and records the judge as a secondary quality lens.
Validate the whole framework offline (no network/API) with
`python3 scripts/bench_selftest.py`. See `configs/benchmarks/README.md` for the full
catalog and how to add a benchmark.

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

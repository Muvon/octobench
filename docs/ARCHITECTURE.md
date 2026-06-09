# Architecture

## Concepts
- **Case**: A task definition with prompts, inputs, fixtures, and scripts.
- **Provider**: A Python implementation that executes a CLI tool and returns normalized telemetry (tokens, cost, latency, output, provider_trace).
- **Executor**: Abstracts *where* commands run (`runners/executor.py`). `HostExecutor` runs local subprocesses; `DockerExecutor` runs each case in its own container (`docker exec`), injecting host auth. Providers and case scripts go through the executor so the rest of the flow is identical in both modes.
- **Runner/Orchestrator**: Coordinates case execution, evidence capture, judging, and scoring (`cli/main.py`). `cli/swebench.py` is a parallel runner for SWE-bench-Live instances (repo-in-image at `/testbed`, verdict from the instance's tests) that reuses the same judge/scoring/results format.
- **Judge**: LLM evaluator with a fixed JSON schema (octomind `judge` role).
- **Report**: JSON aggregation of all runs (`scripts/summary.py` prints a comparison table).

## Case lifecycle
1. Workspace created per case/provider/model combination.
2. `setup.sh` prepares the working dir and is responsible for full setup.
3. A baseline snapshot is taken, then a post-run snapshot is diffed for evidence.
4. Provider runs task and returns normalized metrics (tokens/cost/latency/output).
5. `quality.sh` and `validate.sh` run (bash only).
6. Judge evaluates model output + script logs.

## Scoring
- Judge produces `score` (0-100).
- Efficiency score is computed from absolute latency/cost/tps formula.
- Final score uses global weights:
  - `judge_weight`
  - `efficiency_weight`
- Validation failure always hard-fails.

#!/usr/bin/env bash
set -eo pipefail
cd /home/box/work/muvon/octobench
eval "$(grep "^export " ~/.zshrc)"
export OCTOBENCH_JUDGE_MODELS="openrouter:thinkingmachines/inkling-small,openrouter:minimax/minimax-m3,openrouter:deepseek/deepseek-v4-flash-0731"
export CODEX_BIN=/tmp/codex-0.145.0/codex
.venv/bin/python -m cli.main run --cases cases/dev/oneshot --config configs/run-matrix.cases-codex.yaml \
  --executor docker --image octobench-agent:latest --out results-full-codex --verbosity normal || true
for rj in results-full-codex/*/results.json; do
  .venv/bin/python scripts/rerun_failed.py "$rj" configs/run-matrix.cases-codex.yaml 2 >> /tmp/full-codex-finalize.log 2>&1 || true
  .venv/bin/python scripts/rejudge.py "$rj" >> /tmp/full-codex-finalize.log 2>&1 || true
done
echo "CODEX-BENCH-DONE" | tee /tmp/CODEX-BENCH-DONE

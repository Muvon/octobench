#!/usr/bin/env bash
set -eo pipefail
cd /home/box/work/muvon/octobench
eval "$(grep "^export " ~/.zshrc)"
export OCTOBENCH_JUDGE_MODELS="openrouter:thinkingmachines/inkling-small,openrouter:minimax/minimax-m3,openrouter:deepseek/deepseek-v4-flash-0731"
.venv/bin/python -m cli.main run --cases cases/dev/oneshot --config configs/run-matrix.cases-claude.yaml \
  --executor docker --image octobench-agent:latest --out results-full-claude --verbosity normal || true
echo "FULL-CLAUDE-DONE"

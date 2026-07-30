#!/usr/bin/env bash
set -eo pipefail
cd /home/box/work/muvon/octobench
eval "$(grep "^export " ~/.zshrc)"
export OCTOBENCH_JUDGE_MODEL=ollama:minimax-m3
.venv/bin/python -m cli.main run --cases cases/dev --config configs/run-matrix.cases-claude.yaml \
  --executor docker --image octobench-agent:latest --out results-full-claude --verbosity normal || true
echo "FULL-CLAUDE-DONE"

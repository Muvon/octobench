#!/usr/bin/env bash
set -eo pipefail
cd /home/box/work/muvon/octobench
eval "$(grep "^export " ~/.zshrc)"
export OCTOBENCH_JUDGE_MODEL=ollama:minimax-m3
export OCTOMIND_TAP_CACHE=/tmp/tap-stage
export OCTOMIND_BIN=/tmp/oct-build-musl/x86_64-unknown-linux-musl/release/octomind
.venv/bin/python -m cli.main run --cases cases/dev --config configs/run-matrix.cases-octomind.yaml \
  --executor docker --image octobench-agent:latest --out results-full-octomind --verbosity normal || true
echo "FULL-OCTOMIND-DONE"

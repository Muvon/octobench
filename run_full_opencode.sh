#!/usr/bin/env bash
set -eo pipefail
cd /home/box/work/muvon/octobench
eval "$(grep "^export " ~/.zshrc)"
export OCTOBENCH_JUDGE_MODEL=ollama:minimax-m3
export OPENCODE_BIN=/tmp/opencode-1.18.9/opencode
export OPENCODE_CONFIG_JSON=/home/box/work/muvon/octobench/configs/opencode/opencode.json
# Start after the codex bench finishes (bounded box load / disk).
while [ ! -f /tmp/CODEX-BENCH-DONE ]; do sleep 120; done
.venv/bin/python -m cli.main run --cases cases/dev --config configs/run-matrix.cases-opencode.yaml \
  --executor docker --image octobench-agent:latest --out results-full-opencode --verbosity normal || true
for rj in results-full-opencode/*/results.json; do
  .venv/bin/python scripts/rerun_failed.py "$rj" configs/run-matrix.cases-opencode.yaml 2 >> /tmp/full-opencode-finalize.log 2>&1 || true
  .venv/bin/python scripts/rejudge.py "$rj" >> /tmp/full-opencode-finalize.log 2>&1 || true
done
echo "OPENCODE-BENCH-DONE" | tee /tmp/OPENCODE-BENCH-DONE

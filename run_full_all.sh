#!/usr/bin/env bash
# Overnight full-bench driver: both providers in parallel over cases/dev/oneshot,
# then infra-failure reruns, then degenerate-judge repair.
# Survives the controlling session: run under nohup; progress in /tmp/full-*.log,
# completion marker /tmp/FULL-BENCH-DONE.
set -eo pipefail
cd /home/box/work/muvon/octobench
eval "$(grep "^export " ~/.zshrc)"
export OCTOBENCH_JUDGE_MODEL=ollama:minimax-m3

# Wait for any in-flight bench (round-2 tail) to drain first — the claude
# credential file mount assumes a single concurrent claude run.
while pgrep -f "cli.main run" > /dev/null 2>&1; do sleep 60; done
echo "prior-runs-drained $(date -u +%FT%TZ)" >> /tmp/full-driver.log

bash ./run_full_claude.sh   > /tmp/full-claude.log   2>&1 &
CPID=$!
bash ./run_full_octomind.sh > /tmp/full-octomind.log 2>&1 &
OPID=$!
wait "$CPID" || true
wait "$OPID" || true
echo "both-runs-finished $(date -u +%FT%TZ)" >> /tmp/full-driver.log

for p in claude octomind; do
  matrix="configs/run-matrix.cases-$p.yaml"
  for rj in results-full-$p/*/results.json; do
    [ -f "$rj" ] || continue
    .venv/bin/python scripts/rerun_failed.py "$rj" "$matrix" 2 >> /tmp/full-driver.log 2>&1 || true
    OCTOBENCH_JUDGE_MODEL=ollama:minimax-m3 .venv/bin/python scripts/rejudge.py "$rj" >> /tmp/full-driver.log 2>&1 || true
  done
done

echo "FULL-BENCH-DONE $(date -u +%FT%TZ)" | tee /tmp/FULL-BENCH-DONE >> /tmp/full-driver.log

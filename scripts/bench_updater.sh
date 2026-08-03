#!/usr/bin/env bash
# Keep BENCHMARK.md's results block current while full-bench runs are active.
# Exits (after a final regeneration) once all provider done-markers exist and
# no bench processes remain.
set -eo pipefail
cd /home/box/work/muvon/octobench

regen() {
  .venv/bin/python scripts/update_benchmark.py \
    "opus=results-full-claude/*/results.json" \
    "glm-octomind=results-full-octomind/*/results.json" \
    "gpt56-codex=results-full-codex/*/results.json" \
    "glm-opencode=results-full-opencode/*/results.json" >> /tmp/bench-update.log 2>&1
}

while true; do
  regen
  if [ -f /tmp/CODEX-BENCH-DONE ] && [ -f /tmp/OPENCODE-BENCH-DONE ] \
     && ! pgrep -f rerun_failed > /dev/null && ! pgrep -f "cli.main run" > /dev/null; then
    # Safety net: sweep every results file for degenerate judge verdicts that
    # any dead chain step may have left behind, then regenerate one last time.
    eval "$(grep '^export ' ~/.zshrc)"
    export OCTOBENCH_JUDGE_MODELS="openrouter:thinkingmachines/inkling-small,openrouter:minimax/minimax-m3,openrouter:deepseek/deepseek-v4-flash-0731"
    for rj in results-full-*/*/results.json; do
      .venv/bin/python scripts/rejudge.py "$rj" >> /tmp/bench-update.log 2>&1 || true
    done
    regen
    echo "BENCHMARK-UPDATER-FINAL" >> /tmp/bench-update.log
    break
  fi
  sleep 600
done

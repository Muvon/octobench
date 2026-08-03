#!/usr/bin/env bash
# Run fail-to-pass verification for all long-run cases in parallel.
# Logs to /tmp/lr-verify-<case>.log. Concurrency limited to avoid OOM.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON:-${SCRIPT_DIR}/.venv/bin/python}"
LOGDIR="/tmp/lr-verify-logs"
mkdir -p "${LOGDIR}"

MAX_JOBS=4

cd "${SCRIPT_DIR}"

# Discover every sequence under the longrun tree (no hardcoded list).
# LR_SKIP: substring filter to exclude sequences (e.g. LR_SKIP=simdjson).
CASES=()
for d in cases/dev/longrun/*/*/; do
  [[ -n "${LR_SKIP:-}" && "${d}" == *"${LR_SKIP}"* ]] && continue
  [[ -f "${d}sequence.yaml" ]] && CASES+=("${d%/}")
done

pids=()
run_one() {
  local case_dir="$1"
  local case_id
  case_id="$(basename "$(dirname "${case_dir}")")_$(basename "${case_dir}")"
  local log="${LOGDIR}/${case_id}.log"
  echo "[orchestrator] starting ${case_id} -> ${log}"
  PYTHON="${PYTHON_BIN}" bash scripts/verify_longrun.sh "${case_dir}" > "${log}" 2>&1 &
  pids+=($!)
}

wait_slot() {
  while [[ $(jobs -r | wc -l) -ge ${MAX_JOBS} ]]; do
    sleep 5
  done
}

for c in "${CASES[@]}"; do
  wait_slot
  run_one "${c}"
done

# Wait for all.
echo "[orchestrator] waiting for ${#pids[@]} jobs..."
fail=0
for pid in "${pids[@]}"; do
  if ! wait "${pid}"; then
    fail=$((fail + 1))
  fi
done

echo ""
echo "========================================"
echo "VERIFICATION SUMMARY"
echo "========================================"
for c in "${CASES[@]}"; do
  case_id="$(basename "$(dirname "${c}")")_$(basename "${c}")"
  log="${LOGDIR}/${case_id}.log"
  result="$(grep -E '^RESULT:' "${log}" 2>/dev/null || echo 'NO RESULT')"
  echo "  ${case_id}: ${result}"
done
echo "========================================"
echo "Failed jobs (script exit): ${fail}"

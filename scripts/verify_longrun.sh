#!/usr/bin/env bash
# Prove a long-run sequence end-to-end (fail-to-pass per turn) in the agent
# image. Mirrors the real bench flow: turns run in order and each turn's gold
# source fix STAYS applied for subsequent turns.
#
# Per turn:
#   1. checkout the turn's gold test files
#   2. run test_command      → must FAIL (fix not applied yet)
#   3. apply gold source diff (first-parent, test paths excluded; --3way
#      fallback for context drift from earlier turns)
#   4. run test_command      → must PASS
#   5. restore test files to HEAD, keep the source fix (cumulative)
#
# Usage: scripts/verify_longrun.sh <sequence_dir> [image]
# Example: scripts/verify_longrun.sh cases/dev/longrun/rust/tokio
set -uo pipefail

SEQ_DIR="$(cd "${1:?usage: verify_longrun.sh <sequence_dir> [image]}" && pwd)"
IMAGE="${2:-octobench-agent:latest}"
SEQ_FILE="${SEQ_DIR}/sequence.yaml"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON:-${SCRIPT_DIR}/.venv/bin/python}"

[[ -f "${SEQ_FILE}" ]] || { echo "ERROR: ${SEQ_FILE} not found"; exit 1; }

SEQ_ID="$("${PYTHON_BIN}" -c "import yaml; print(yaml.safe_load(open('${SEQ_FILE}'))['id'])")"
REPO_URL="$("${PYTHON_BIN}" -c "import yaml; print(yaml.safe_load(open('${SEQ_FILE}'))['meta']['repo'])")"
NUM_TURNS="$("${PYTHON_BIN}" -c "import yaml; print(len(yaml.safe_load(open('${SEQ_FILE}'))['turns']))")"

echo "=== verify_longrun: ${SEQ_ID} (${NUM_TURNS} turns) ==="

WS="$(mktemp -d "${TMPDIR:-/tmp}/lr-verify.XXXXXX")"
NAME="lr-verify-$$"
KEEPDIR="${LR_KEEP_LOGS_DIR:-/tmp/lr-verify-keep}/${SEQ_ID}"
cleanup() {
  mkdir -p "${KEEPDIR}" && cp "${WS}"/.*.log "${KEEPDIR}/" 2>/dev/null || true
  docker exec "${NAME}" find /workspace -mindepth 1 -delete >/dev/null 2>&1 || true
  docker rm -f "${NAME}" >/dev/null 2>&1 || true
  rmdir "${WS}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run -d --name "${NAME}" -w /workspace \
  -v "${WS}:/workspace" -v "${SEQ_DIR}:/case:ro" \
  -e CASE_DIR=/case -e WORKDIR=/workspace \
  "${IMAGE}" sleep infinity >/dev/null

step() { docker exec -w /workspace "${NAME}" bash "$@"; }

echo "--- setup ---"
if ! step /case/setup.sh > "${WS}/.setup.log" 2>&1; then
  echo "SETUP FAILED"; tail -30 "${WS}/.setup.log"; exit 1
fi
echo "setup OK"

BAD=0
for ((i=0; i<NUM_TURNS; i++)); do
  # Extract turn fields with unambiguous markers (test paths may be many).
  TURN_JSON="$("${PYTHON_BIN}" - "${SEQ_FILE}" "${i}" <<'PYEOF'
import json, sys, yaml
t = yaml.safe_load(open(sys.argv[1]))["turns"][int(sys.argv[2])]
print(json.dumps({
    "name": t["name"],
    "gold": t["gold_sha"],
    "paths": t["test_paths"],
    "cmd": t["test_command"],
}))
PYEOF
)"
  TURN_NAME="$(echo "${TURN_JSON}" | "${PYTHON_BIN}" -c "import json,sys; print(json.load(sys.stdin)['name'])")"
  GOLD_SHA="$(echo "${TURN_JSON}" | "${PYTHON_BIN}" -c "import json,sys; print(json.load(sys.stdin)['gold'])")"
  TEST_PATHS="$(echo "${TURN_JSON}" | "${PYTHON_BIN}" -c "import json,sys; print('\n'.join(json.load(sys.stdin)['paths']))")"
  TEST_CMD="$(echo "${TURN_JSON}" | "${PYTHON_BIN}" -c "import json,sys; print(json.load(sys.stdin)['cmd'])")"

  echo ""
  echo "--- turn $((i+1))/${NUM_TURNS}: ${TURN_NAME} (gold ${GOLD_SHA:0:12}) ---"

  FETCH_TESTS="$(cat <<EOS
set -euo pipefail
git remote add origin '${REPO_URL}' 2>/dev/null || true
git fetch -q --depth 2 origin '${GOLD_SHA}'
while IFS= read -r t; do
  [[ -n "\$t" ]] && git checkout -q '${GOLD_SHA}' -- "\$t"
done <<< '${TEST_PATHS}'
# checkout stages new files; unstage so the turn commit captures only the
# gold source patch, never test content.
while IFS= read -r t; do
  [[ -n "\$t" ]] && git reset -q HEAD -- "\$t" 2>/dev/null || true
done <<< '${TEST_PATHS}'
EOS
)"
  if ! step -c "${FETCH_TESTS}" > "${WS}/.t$((i+1)).fetch.log" 2>&1; then
    echo "  FETCH/CHECKOUT FAILED"; tail -20 "${WS}/.t$((i+1)).fetch.log"
    BAD=$((BAD+1)); continue
  fi

  if step -c "cd /workspace && ${TEST_CMD}" > "${WS}/.t$((i+1)).pre.log" 2>&1; then
    echo "  BAD: tests already PASS before the fix"
    tail -5 "${WS}/.t$((i+1)).pre.log"
    BAD=$((BAD+1))
  else
    echo "  fail-at-pre OK"
  fi

  # Apply with --index so a follow-up commit captures exactly the patch
  # (including new files). On failure, hard-reset so a conflicted 3-way apply
  # can never poison subsequent turns, and remove new files the failed patch
  # left on disk.
  GOLD_APPLY="$(cat <<EOS
set -euo pipefail
ex=(":(exclude,icase)*changelog*" ":(exclude)*.md")
while IFS= read -r t; do [[ -n "\$t" ]] && ex+=(":(exclude)\$t"); done <<< '${TEST_PATHS}'
git diff --binary '${GOLD_SHA}^1' '${GOLD_SHA}' -- . "\${ex[@]}" > /tmp/gold.patch
if git apply --index /tmp/gold.patch 2>/dev/null \
   || git apply --3way --index /tmp/gold.patch; then
  git -c user.email=verify@octobench -c user.name=verify \
    commit -qm 'turn $((i+1)) gold' 2>/dev/null || true
else
  git reset -q --hard HEAD
  grep '^+++ b/' /tmp/gold.patch | sed 's|^+++ b/||' | while IFS= read -r f; do
    git ls-files --error-unmatch "\$f" >/dev/null 2>&1 || rm -f "\$f"
  done
  exit 1
fi
EOS
)"
  if ! step -c "${GOLD_APPLY}" > "${WS}/.t$((i+1)).gold.log" 2>&1; then
    echo "  GOLD APPLY FAILED"; tail -20 "${WS}/.t$((i+1)).gold.log"
    BAD=$((BAD+1)); continue
  fi

  if ! step -c "cd /workspace && ${TEST_CMD}" > "${WS}/.t$((i+1)).post.log" 2>&1; then
    echo "  BAD: tests still FAIL with gold source applied"
    tail -20 "${WS}/.t$((i+1)).post.log"
    BAD=$((BAD+1))
  else
    echo "  pass-after-gold OK"
  fi

  # Restore test files to HEAD (base); keep the applied source fix.
  RESTORE="$(cat <<EOS
while IFS= read -r t; do
  [[ -n "\$t" ]] && { git checkout -q HEAD -- "\$t" 2>/dev/null || rm -f "\$t"; }
done <<< '${TEST_PATHS}'
git remote remove origin 2>/dev/null || true
EOS
)"
  step -c "${RESTORE}" >/dev/null 2>&1 || true
done

echo ""
if [[ ${BAD} -gt 0 ]]; then
  echo "RESULT: FAIL — ${BAD} broken leg(s) across ${NUM_TURNS} turns"
  exit 1
fi
echo "RESULT: OK — all ${NUM_TURNS} turns fail-to-pass proven"

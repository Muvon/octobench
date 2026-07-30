#!/usr/bin/env bash
# Prove a real-commit case end-to-end (fail-to-pass) in the agent image:
#   1. setup.sh          → workspace at BASE (pre-change state)
#   2. validate.sh       → must FAIL (held-out tests exercise the missing change)
#   3. apply gold source → checkout the gold commit's non-test paths
#   4. validate.sh       → must PASS (the real change satisfies the tests)
#
# Usage: scripts/verify_case.sh <case_dir> [image]
# Reads repo/base_sha/gold_sha/test_paths meta from the case's case.yaml.
set -uo pipefail

CASE_DIR="$(cd "${1:?usage: verify_case.sh <case_dir> [image]}" && pwd)"
IMAGE="${2:-octobench-agent:latest}"
CASE_ID="$(basename "${CASE_DIR}")"

read -r REPO_URL GOLD_SHA < <("${PYTHON:-python3}" - "$CASE_DIR/case.yaml" <<'EOF'
import sys, yaml
c = yaml.safe_load(open(sys.argv[1]))
print(c["meta"]["repo"], c["meta"]["gold_sha"])
EOF
)
TEST_PATHS="$("${PYTHON:-python3}" - "$CASE_DIR/case.yaml" <<'EOF'
import sys, yaml
c = yaml.safe_load(open(sys.argv[1]))
print("\n".join(c["meta"]["test_paths"]))
EOF
)"

WS="$(mktemp -d "${TMPDIR:-/tmp}/ob-verify.XXXXXX")"
NAME="ob-verify-$$"
cleanup() { docker rm -f "${NAME}" >/dev/null 2>&1; rm -rf "${WS}"; }
trap cleanup EXIT

docker run -d --name "${NAME}" -w /workspace \
  -v "${WS}:/workspace" -v "${CASE_DIR}:/case:ro" \
  -e CASE_DIR=/case -e WORKDIR=/workspace \
  "${IMAGE}" sleep infinity >/dev/null

step() { docker exec -w /workspace "${NAME}" bash "$@"; }

echo "[verify:${CASE_ID}] setup"
if ! step /case/setup.sh > "${WS}/.setup.log" 2>&1; then
  echo "[verify:${CASE_ID}] SETUP FAILED"; tail -30 "${WS}/.setup.log"; exit 1
fi

echo "[verify:${CASE_ID}] validate at BASE (expect FAIL)"
if step /case/validate.sh > "${WS}/.val-base.log" 2>&1; then
  echo "[verify:${CASE_ID}] BAD: tests already pass at BASE (not fail-to-pass)"
  tail -30 "${WS}/.val-base.log"; exit 1
fi

echo "[verify:${CASE_ID}] apply gold source paths"
GOLD_APPLY="$(cat <<EOS
set -euo pipefail
git remote add origin '${REPO_URL}' 2>/dev/null || true
# depth 2: the gold's first parent (== the case BASE) must exist so the
# first-parent diff works for merge commits too. Applying the diff (instead of
# checking out paths) also covers files the gold commit deletes or renames.
git fetch -q --depth 2 origin '${GOLD_SHA}'
ex=()
while IFS= read -r t; do [[ -n "\$t" ]] && ex+=(":(exclude)\$t"); done <<< '${TEST_PATHS}'
git diff '${GOLD_SHA}^1' '${GOLD_SHA}' -- . "\${ex[@]}" | git apply
git status --porcelain | head -20
EOS
)"
if ! step -c "${GOLD_APPLY}" > "${WS}/.gold.log" 2>&1; then
  echo "[verify:${CASE_ID}] GOLD APPLY FAILED"; tail -30 "${WS}/.gold.log"; exit 1
fi

echo "[verify:${CASE_ID}] validate with gold (expect PASS)"
if ! step /case/validate.sh > "${WS}/.val-gold.log" 2>&1; then
  echo "[verify:${CASE_ID}] BAD: tests fail even with gold source"
  tail -40 "${WS}/.val-gold.log"; exit 1
fi

echo "[verify:${CASE_ID}] OK: fail-to-pass proven"

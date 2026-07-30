#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/eslint/eslint"
GOLD_SHA="90910715011211a20d011d807d398a7005127f35"
TEST_PATHS=(tests/lib/rules/no-unreachable-loop.js)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

npx mocha "${TEST_PATHS[@]}"

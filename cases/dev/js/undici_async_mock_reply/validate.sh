#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nodejs/undici"
GOLD_SHA="6de5935f8add8d1fe3734281a8db1eb28f7fe729"
TEST_PATHS=(test/mock-interceptor.js)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

node --test test/mock-interceptor.js

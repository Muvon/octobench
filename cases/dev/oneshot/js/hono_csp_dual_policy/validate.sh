#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/honojs/hono"
GOLD_SHA="402eb3abe561914f41ee0f8e37f1d7f211f1ee51"
TEST_PATHS=(src/middleware/secure-headers/index.test.ts)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

npx vitest run "${TEST_PATHS[@]}"

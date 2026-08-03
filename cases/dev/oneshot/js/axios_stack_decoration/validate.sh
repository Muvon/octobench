#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/axios/axios"
GOLD_SHA="a75bf44647e5132e39b778730394b0a2b983265c"
TEST_PATHS=(tests/unit/core/Axios.test.js)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

npx vitest run --project unit tests/unit/core/Axios.test.js

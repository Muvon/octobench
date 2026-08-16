#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pestphp/pest"
GOLD_SHA="2e58918201f047cd9179e8944faa6dc478513815"
TEST_PATHS=(tests/Features/Tia/CompleteRunWriteTier.php)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

php8.4 bin/pest "${TEST_PATHS[@]}" --filter 'last test is skipped from a hook'

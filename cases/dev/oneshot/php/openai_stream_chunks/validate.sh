#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/openai-php/client"
GOLD_SHA="bfb0ed920df3eca610bebc5b914cefeca143c415"
TEST_PATHS=(tests/Responses/StreamResponse.php)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

vendor/bin/pest "${TEST_PATHS[@]}"

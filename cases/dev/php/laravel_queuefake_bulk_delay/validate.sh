#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/laravel/framework"
GOLD_SHA="af9d320df90c0a69c230d35c17370e7db6a4035d"
TEST_PATHS=(tests/Support/SupportTestingQueueFakeTest.php)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

vendor/bin/phpunit "${TEST_PATHS[@]}"

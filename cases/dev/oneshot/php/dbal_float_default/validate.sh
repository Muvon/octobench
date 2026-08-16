#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/doctrine/dbal"
GOLD_SHA="5f46f878094f6eddca2de3cc47364b29954b4e7a"
TEST_PATHS=(tests/Functional/Schema/ComparatorTest.php)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

vendor/bin/phpunit "${TEST_PATHS[@]}" --filter testFloatDefaultValueComparison

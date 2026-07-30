#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/guzzle/guzzle"
GOLD_SHA="7f8b93d1a9bed5bdd4ecb4e40c4a26898c8826e4"
TEST_PATHS=(tests/Cookie/CookieJarTest.php)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

vendor/bin/phpunit tests/Cookie/CookieJarTest.php

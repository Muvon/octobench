#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/laravel/framework"
GOLD_SHA="d36158ef41b8b2206ffa75cc09abb4e0864476e6"
TEST_PATHS=(tests/Http/HttpRequestTest.php)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

# Whole file: the new ordering assertion plus the surrounding Request::all()
# regression coverage, so a fix that reorders keys correctly but breaks
# precedence or explicit-key selection still fails.
php8.4 vendor/bin/phpunit --no-coverage "${TEST_PATHS[@]}"

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/Seldaek/monolog"
GOLD_SHA="108867b3552775777dea2c71e014e233147f440f"
TEST_PATHS=(tests/Monolog/Formatter/NormalizerFormatterTest.php)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

vendor/bin/phpunit "${TEST_PATHS[@]}"

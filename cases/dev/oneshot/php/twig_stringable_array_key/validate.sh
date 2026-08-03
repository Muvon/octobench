#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/twigphp/Twig"
GOLD_SHA="8ada671fc39a235b48ef7d18020ab43658e98917"
TEST_PATHS=(tests/TemplateTest.php)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

vendor/bin/simple-phpunit "${TEST_PATHS[@]}"

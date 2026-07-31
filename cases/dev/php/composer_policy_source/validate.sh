#!/usr/bin/env bash
set -euo pipefail

GOLD_SHA="bb38c69cac82c5c6caeda8721715b0f9f9e7b6c2"
TEST_ONE="tests/Composer/Test/Advisory/AuditorTest.php"
TEST_TWO="tests/Composer/Test/DependencyResolver/ProblemTest.php"

git remote add origin https://github.com/composer/composer 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_ONE}" "${TEST_TWO}"
vendor/bin/simple-phpunit "${TEST_ONE}" "${TEST_TWO}"

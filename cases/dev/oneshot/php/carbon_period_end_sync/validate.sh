#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/briannesbitt/Carbon"
GOLD_SHA="2c330722d22555ad20f3bcfdb2c1ba5a56a0b5f5"
TEST_PATHS=(tests/CarbonPeriod/GettersTest.php)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Restore the upstream PHPUnit harness so agent edits cannot bypass the tests.
git checkout -q "${GOLD_SHA}" -- tests/AbstractTestCase.php tests/CarbonPeriod/Fixtures/CarbonPeriodFactory.php phpunit.xml.dist
git -c safe.directory='*' clean -fdq -- tests/CarbonPeriod/Fixtures
rm -f phpunit.xml

vendor/bin/phpunit "${TEST_PATHS[@]}"

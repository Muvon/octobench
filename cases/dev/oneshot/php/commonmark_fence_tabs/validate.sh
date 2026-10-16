#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/thephpleague/commonmark"
GOLD_SHA="51b529fd295ade2e641e8a6152e72c16ce9735ac"
TEST_PATHS=(tests/functional/data/fenced_code_tabs.md tests/functional/data/fenced_code_tabs.html)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Restore the upstream PHPUnit harness and globbed data so agent edits cannot bypass the tests.
git checkout -q "${GOLD_SHA}" -- tests/functional/LocalDataTest.php tests/functional/data phpunit.xml.dist
git -c safe.directory='*' clean -fdq -- tests/functional
rm -f phpunit.xml

vendor/bin/phpunit --no-coverage tests/functional/LocalDataTest.php

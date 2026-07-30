#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/thephpleague/commonmark"
GOLD_SHA="51b529fd295ade2e641e8a6152e72c16ce9735ac"
TEST_PATHS=(tests/functional/data/fenced_code_tabs.md tests/functional/data/fenced_code_tabs.html)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# LocalDataTest globs every .md/.html pair in the data dir; drop untracked
# fixtures an agent may have left so its own repro files cannot fail the case.
git -c safe.directory='*' clean -fq tests/functional/data || true

vendor/bin/phpunit --no-coverage tests/functional/LocalDataTest.php

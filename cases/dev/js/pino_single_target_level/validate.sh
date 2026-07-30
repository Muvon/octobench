#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pinojs/pino"
GOLD_SHA="ea99eee063c783964f51bf3ac2c2c2815263056e"
TEST_PATHS=(test/transport/core.test.js)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

node --test --test-name-pattern "single target in targets array" test/transport/core.test.js

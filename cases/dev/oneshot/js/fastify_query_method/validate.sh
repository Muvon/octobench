#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/fastify/fastify"
GOLD_SHA="6e680c3e8150071be96cba6b30e1d74487559b54"
TEST_PATHS=(test/rfc-10008.test.js test/route-shorthand.test.js test/internals/all.test.js)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

node --test "${TEST_PATHS[@]}"

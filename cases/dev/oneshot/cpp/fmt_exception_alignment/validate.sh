#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/fmtlib/fmt"
GOLD_SHA="cde18a38bbd960a2e803b76880fbbf4b4ffb3cd7"
TEST_PATHS=(test/std-test.cc)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cmake --build build --target std-test -j"$(nproc)"
ctest --test-dir build -R '^std-test$' --output-on-failure

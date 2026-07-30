#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/fmtlib/fmt"
GOLD_SHA="128ba144ab85ddd0ad9ea39f2febdfb51802cb1b"
TEST_PATHS=(test/printf-test.cc)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cmake --build build --target printf-test -j"$(nproc)"
ctest --test-dir build -R '^printf-test$' --output-on-failure

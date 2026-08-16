#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/duckdb/duckdb"
GOLD_SHA="5366dc3925ce0f981c2110cf4bf8e39fa1dd6fde"
TEST_PATHS=(test/common/test_external_file_cache.cpp)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cmake --build build/debug --target unittest -j"$(nproc)"
build/debug/test/unittest '[external_file_cache]'

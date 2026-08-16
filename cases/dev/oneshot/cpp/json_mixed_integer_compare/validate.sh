#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nlohmann/json"
GOLD_SHA="6285225fd068df42d043721f3bef65fca48c59fb"
TEST_PATHS=(tests/src/unit-comparison.cpp)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cmake --build build --target test-comparison_cpp20 -j"$(nproc)"
ctest --test-dir build -R '^test-comparison_cpp20$' --output-on-failure

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/simdjson/simdjson"
GOLD_SHA="e3720ba824500473a20d095779afc129511c832f"
TEST_PATHS=(tests/dom/big_integer_tests.cpp tests/ondemand/ondemand_number_tests.cpp)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cmake --build build --target big_integer_tests ondemand_number_tests -j"$(nproc)"
ctest --test-dir build -R '^(big_integer_tests|ondemand_number_tests)$' --output-on-failure

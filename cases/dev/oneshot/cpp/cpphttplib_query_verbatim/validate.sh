#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/yhirose/cpp-httplib"
GOLD_SHA="3fe32b63b42d7b273cd4d76d69df0097560375d6"
TEST_PATHS=(test/test.cc)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cmake --build build --target httplib-test -j"$(nproc)"

# The test binary reads fixture files copied next to it in the build tree.
cd build/test
./httplib-test --gtest_filter='PathUrlEncodeTest.*'

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/jbeder/yaml-cpp"
GOLD_SHA="847020a9cd706412eae6d73a0ba12ec02428bc5b"
TEST_PATHS=(test/node/node_test.cpp)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cmake --build build --target yaml-cpp-tests -j"$(nproc)"
./build/test/yaml-cpp-tests --gtest_filter='NodeTest.*'

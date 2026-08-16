#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/google/benchmark"
GOLD_SHA="977dfc2e3d90074956355aa2bde009ab4796145c"
TEST_PATHS=(test/CMakeLists.txt test/memory_manager_ordering_gtest.cc)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DBENCHMARK_ENABLE_TESTING=ON -DBENCHMARK_ENABLE_GTEST_TESTS=ON \
  -DBENCHMARK_DOWNLOAD_DEPENDENCIES=ON \
  -DBENCHMARK_ENABLE_INSTALL=OFF > /dev/null
cmake --build build --target memory_manager_ordering_gtest -j"$(nproc)"
ctest --test-dir build -R '^memory_manager_ordering_gtest$' --output-on-failure

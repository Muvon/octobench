#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/jbeder/yaml-cpp"
GOLD_SHA="ee52744a3196c32f29536b4671c703146cac9cb6"
TEST_PATHS=(test/integration/emitter_test.cpp)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Restore every upstream source linked into the test binary so agent edits cannot replace it.
git checkout -q "${GOLD_SHA}" -- CMakeLists.txt test
git -c safe.directory='*' clean -fdq -- test

cmake --build build --target yaml-cpp-tests -j"$(nproc)"
./build/test/yaml-cpp-tests

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/catchorg/Catch2"
GOLD_SHA="572f96b8febec9dd14ac5284e6a959a7246325c8"
TEST_PATHS=(tests/SelfTest/IntrospectiveTests/TextFlow.tests.cpp)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cmake --build build --target SelfTest -j"$(nproc)"
./build/tests/SelfTest "[TextFlow]" --order decl

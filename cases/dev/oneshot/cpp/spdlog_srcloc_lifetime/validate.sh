#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/gabime/spdlog"
GOLD_SHA="03bec982c294c54cb16452d2be083d73843849b9"
TEST_PATHS=(tests/test_ringbuffer.cpp)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cmake --build build -j"$(nproc)" --target spdlog-utests
./build/tests/spdlog-utests "[ringbuffer]"

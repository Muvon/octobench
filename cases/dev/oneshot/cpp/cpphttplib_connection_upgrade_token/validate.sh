#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/yhirose/cpp-httplib"
GOLD_SHA="ffe2a1c1e9e0c87b44c1b25ddb5b6a34b30fa6c9"
TEST_PATHS=(test/test.cc)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cmake --build build --target httplib-test -j"$(nproc)"

# Whole WebSocket suite: the three token-matching tests plus the 22 existing
# handshake tests, so a fix that rejects the bypasses by breaking legitimate
# upgrades still fails.
cd build/test
./httplib-test --gtest_filter='WebSocketTest.*'

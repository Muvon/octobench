#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/yhirose/cpp-httplib"
BASE_SHA="0ae93881b44bf94437843403bfcdc4f50445992e"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

# test/CMakeLists.txt requires libcurl headers. Present in the agent image once
# libcurl4-openssl-dev is added; this guard keeps the case runnable meanwhile.
if ! pkg-config --exists libcurl 2>/dev/null; then
  (apt-get update -qq && apt-get install -y -qq --no-install-recommends libcurl4-openssl-dev) \
    || (sudo apt-get update -qq && sudo apt-get install -y -qq --no-install-recommends libcurl4-openssl-dev)
fi

# Configure now, while the network is available: when GTest is not installed
# system-wide, test/CMakeLists.txt fetches googletest at CONFIGURE time. After
# this step validate.sh only needs to rebuild, so it stays offline.
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DHTTPLIB_TEST=ON -DHTTPLIB_REQUIRE_OPENSSL=OFF -DHTTPLIB_COMPILE=ON > /dev/null
cmake --build build --target httplib-test -j"$(nproc)" > /dev/null

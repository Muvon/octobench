#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/yhirose/cpp-httplib"
BASE_SHA="2004668509e983a1b5a8bed6f4b9c87840330df4"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

if ! pkg-config --exists libcurl 2>/dev/null; then
  (apt-get update -qq && apt-get install -y -qq --no-install-recommends libcurl4-openssl-dev) \
    || (sudo apt-get update -qq && sudo apt-get install -y -qq --no-install-recommends libcurl4-openssl-dev)
fi

# Header-only build (no HTTPLIB_COMPILE): the held-out tests reach the handshake
# predicates in namespace detail, which exist at base as inline definitions. The
# split header/implementation build only exposes what the declaration section
# forward-declares, so under it the gold tests fail to COMPILE against any
# implementation but gold's own — the case would measure internal API shape
# instead of behaviour.
#
# Configure now, while the network is available: without a system GTest,
# test/CMakeLists.txt fetches googletest at CONFIGURE time. Validation then
# only rebuilds, so it stays offline.
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DHTTPLIB_TEST=ON -DHTTPLIB_REQUIRE_OPENSSL=OFF > /dev/null
cmake --build build --target httplib-test -j"$(nproc)" > /dev/null

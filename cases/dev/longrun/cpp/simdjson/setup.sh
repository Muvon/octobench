#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/simdjson/simdjson"
BASE_SHA="396ca141fd737f96744210eedc81573a93f3d26b"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# SIMDJSON_DEVELOPER_MODE=ON is load-bearing: without it the root CMakeLists
# returns before add_subdirectory(tests) and NO test target exists.
# The two defines are load-bearing too: NAN_INF gates turn-2 assertions,
# ALLOW_INCOMPLETE_JSON gates turn-1's entire test block.
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DSIMDJSON_DEVELOPER_MODE=ON \
  -DSIMDJSON_ENABLE_NAN_INF=ON \
  -DCMAKE_CXX_FLAGS="-DSIMDJSON_EXPERIMENTAL_ALLOW_INCOMPLETE_JSON=1" > /dev/null
cmake --build build -j"$(nproc)" > /dev/null 2>&1 || true

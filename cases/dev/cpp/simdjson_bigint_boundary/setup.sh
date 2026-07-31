#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/simdjson/simdjson"
BASE_SHA="8e6bac94877f2d3d026000d36ce81e0aaf38d26f"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DSIMDJSON_DEVELOPER_MODE=ON -DSIMDJSON_COMPETITION=OFF \
  -DSIMDJSON_GOOGLE_BENCHMARKS=OFF > /dev/null
cmake --build build --target big_integer_tests ondemand_number_tests -j"$(nproc)" > /dev/null

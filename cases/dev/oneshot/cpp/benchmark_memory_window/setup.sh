#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/google/benchmark"
BASE_SHA="bb682b4d7f6cf8bf9b01d26ea5498b9cc5115c3b"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DBENCHMARK_ENABLE_TESTING=ON -DBENCHMARK_ENABLE_GTEST_TESTS=ON \
  -DBENCHMARK_DOWNLOAD_DEPENDENCIES=ON \
  -DBENCHMARK_ENABLE_INSTALL=OFF > /dev/null
cmake --build build --target memory_results_gtest -j"$(nproc)" > /dev/null

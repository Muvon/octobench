#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/gabime/spdlog"
BASE_SHA="8671ca4d492c8ee1cdfd3dd88afb9f88dd268178"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B v2.x
git remote remove origin

# ASan build: the reported bug is a use-after-scope; sanitizer makes the
# failure deterministic instead of depending on freed-heap contents.
# Catch2 v3 is FetchContent-cloned here (setup has network; validate does not
# refetch).
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DSPDLOG_BUILD_TESTS=ON -DSPDLOG_BUILD_EXAMPLE=OFF \
  -DSPDLOG_SANITIZE_ADDRESS=ON > /dev/null
cmake --build build -j"$(nproc)" --target spdlog-utests > /dev/null

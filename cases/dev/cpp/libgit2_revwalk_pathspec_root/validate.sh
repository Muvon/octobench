#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/libgit2/libgit2"
GOLD_SHA="9e1c61e0924de72d44ecabe43ccb02820ca68981"
TEST_PATHS=(tests/libgit2/revwalk/pathspec.c)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

# The clar suite index is generated from a configure-time GLOB over tests/, so a
# NEW test file only enters the suite after cmake is re-run.
cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTS=ON -DBUILD_CLI=OFF -DBUILD_EXAMPLES=OFF \
  -DUSE_HTTPS=OFF -DUSE_SSH=OFF > /dev/null
cmake --build build --target libgit2_tests -j"$(nproc)"

./build/libgit2_tests -srevwalk::pathspec

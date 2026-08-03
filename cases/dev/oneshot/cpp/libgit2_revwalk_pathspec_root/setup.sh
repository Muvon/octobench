#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/libgit2/libgit2"
BASE_SHA="32b564e63f9639eaf5ee90fb7a95b3a650156cbd"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# Tests only; no network transports so the build needs no TLS/SSH libraries.
cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTS=ON -DBUILD_CLI=OFF -DBUILD_EXAMPLES=OFF \
  -DUSE_HTTPS=OFF -DUSE_SSH=OFF > /dev/null
cmake --build build --target libgit2_tests -j"$(nproc)" > /dev/null

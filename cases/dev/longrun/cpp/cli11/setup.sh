#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/CLIUtils/CLI11"
BASE_SHA="d15c2ee1bb35e6ad2ff6d3f82369d354b8e035f7"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# BUILD_TESTING=ON is the test-gating flag (CLI11_BUILD_TESTS depends on it).
# C++17 matches upstream CI. Catch2 header is downloaded at configure time.
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DCMAKE_CXX_STANDARD=17 > /dev/null
cmake --build build -j"$(nproc)" > /dev/null 2>&1 || true

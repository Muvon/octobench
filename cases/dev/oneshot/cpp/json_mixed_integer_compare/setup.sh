#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nlohmann/json"
BASE_SHA="21af527e756435701f23e01aa8ea8dab6e050c90"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B develop
git remote remove origin

cmake -S . -B build -G Ninja -DJSON_BuildTests=ON \
  -DJSON_TestStandards=20 -DCMAKE_BUILD_TYPE=Release > /dev/null
cmake --build build --target test-comparison_cpp20 -j"$(nproc)" > /dev/null

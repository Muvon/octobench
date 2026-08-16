#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/fmtlib/fmt"
BASE_SHA="be39437ee71162931d3d06d523b4544029656955"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DFMT_TEST=ON -DFMT_DOC=OFF -DFMT_INSTALL=OFF > /dev/null
cmake --build build --target std-test -j"$(nproc)" > /dev/null

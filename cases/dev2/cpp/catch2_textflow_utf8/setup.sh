#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/catchorg/Catch2"
BASE_SHA="8492fd444e42f331f48611d2b5ef11c8ce338423"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B devel
git remote remove origin

cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 \
  -DCATCH_DEVELOPMENT_BUILD=ON -DCATCH_BUILD_TESTING=ON \
  -DCATCH_ENABLE_WERROR=OFF -DCATCH_INSTALL_DOCS=OFF -DCATCH_BUILD_EXAMPLES=OFF \
  -DCATCH_BUILD_EXTRA_TESTS=OFF -DCATCH_BUILD_BENCHMARKS=OFF > /dev/null
cmake --build build --target SelfTest -j"$(nproc)" > /dev/null

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/opencv/opencv"
BASE_SHA="eccd1c43c4d07816c434548d6ce1cf37126c1945"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_LIST=geometry,imgcodecs,videoio,ts \
  -DBUILD_TESTS=ON \
  -DBUILD_PERF_TESTS=OFF \
  -DBUILD_EXAMPLES=OFF \
  -DBUILD_opencv_apps=OFF
cmake --build build --target opencv_test_geometry -j"$(nproc)"

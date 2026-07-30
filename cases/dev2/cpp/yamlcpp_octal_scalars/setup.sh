#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/jbeder/yaml-cpp"
BASE_SHA="eadeac64e1a0619b5efa5a5674b5edb1a71a8885"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTING=ON -DYAML_CPP_BUILD_TESTS=ON > /dev/null
cmake --build build --target yaml-cpp-tests -j"$(nproc)" > /dev/null

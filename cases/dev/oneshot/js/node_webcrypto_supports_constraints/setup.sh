#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nodejs/node"
BASE_SHA="f914e45b2d3b871d0da03f238415642a308386f2"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

CC=clang-19 CXX=clang++-19 ./configure --ninja \
  --without-intl \
  --without-inspector \
  --without-node-snapshot \
  --node-builtin-modules-path="$(pwd)"
ninja -C out/Release node -j"$(nproc)"
test -x out/Release/node

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/ada-url/ada"
BASE_SHA="1e3b300977d5f2980ae0f64633a1c9fe025901df"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# ADA_TESTING=ON is load-bearing (defaults OFF; also enables the std-regex
# provider the urlpattern tests need). CPM downloads GTest+simdjson at
# configure time — network is allowed here, never at test time.
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DADA_TESTING=ON > /dev/null
cmake --build build -j"$(nproc)" > /dev/null 2>&1 || true

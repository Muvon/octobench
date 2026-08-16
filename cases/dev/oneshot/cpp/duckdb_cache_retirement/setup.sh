#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/duckdb/duckdb"
BASE_SHA="ca9bf23600423863cf23c2762dee0b4c54945e42"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

GEN=ninja make debug -j"$(nproc)" > /dev/null

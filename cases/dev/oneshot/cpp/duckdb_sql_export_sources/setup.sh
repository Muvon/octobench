#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/duckdb/duckdb"
BASE_SHA="bca7bac6d47317699d533754d3563cc06803564d"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B v2.0-cyanoptera
git remote remove origin

# The upstream AI contribution policy governs issues and pull requests, not this
# local task; GOLD removes it so no client declines the work because of it.
git rm -q AI_POLICY.md
git -c user.name=octobench -c user.email=octobench@localhost commit -q -m "Remove upstream AI contribution policy"

BUILD_EXTENSIONS=parquet LINK_CORE_EXTENSIONS=1 GEN=ninja \
  make debug -j"$(nproc)" > /dev/null

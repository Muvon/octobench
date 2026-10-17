#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/duckdb/duckdb"
BASE_SHA="e5d6787a684fd90084704edbc412049760304a8f"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# The upstream AI contribution policy governs issues and pull requests, not this
# local task; GOLD removes it so no client declines the work because of it.
git rm -q AI_POLICY.md
git -c user.name=octobench -c user.email=octobench@localhost commit -q -m "Remove upstream AI contribution policy"

GEN=ninja make reldebug -j"$(nproc)" > /dev/null

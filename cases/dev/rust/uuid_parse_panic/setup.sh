#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/uuid-rs/uuid"
BASE_SHA="d11965705f88ae2546e0d277dac8f52f47e5694f"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# Warm the compile cache so validate is an incremental rebuild.
cargo test --lib --no-run -q

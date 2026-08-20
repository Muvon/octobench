#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/hyperium/hyper"
BASE_SHA="fa3a4b2c04c12fd849dc50abaceba32c4d436069"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

# Warm the dependency graph and the test profile while the network is open, so
# validation only has to recompile the crate itself.
cargo fetch --quiet
cargo test --features full --lib --no-run --quiet

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/GitoxideLabs/gitoxide"
BASE_SHA="5708de4346e9c800ed01a8c4d7cdbe3ab86b1740"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# Leaf crates only — the heavy `gix` top crate is never built. Default features.
cargo fetch -q 2>/dev/null || true
cargo test -q -p gix-config -p gix-config-value -p gix-mailmap -p gix-filter --no-run 2>/dev/null || true

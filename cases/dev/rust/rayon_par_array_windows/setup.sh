#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/rayon-rs/rayon"
BASE_SHA="56bbf0623b9ad3cd6e91e169c5a8a1c10b319b4b"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# Held-out tests use std slice::array_windows (stable since 1.94); fail fast on
# an older toolchain instead of misreporting an uncompilable case.
rustc --version | awk '{split($2,v,"."); exit !(v[1]>1 || v[2]>=94)}'

# Warm the compile cache so validate is an incremental rebuild.
cargo test -p rayon --no-run -q --test producer_split_at --test clones --test debug

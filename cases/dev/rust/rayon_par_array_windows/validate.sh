#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/rayon-rs/rayon"
GOLD_SHA="c9ae0472072c60cc9d911c16fd42cd1eb84a5d0a"
TEST_PATHS=(tests/producer_split_at.rs tests/clones.rs tests/debug.rs)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cargo test -p rayon --test producer_split_at
cargo test -p rayon --test clones
cargo test -p rayon --test debug

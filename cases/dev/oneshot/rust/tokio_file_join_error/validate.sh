#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/tokio-rs/tokio"
GOLD_SHA="83e9c57cee80a93e6e3887077e354fe8a24f3ea8"
TEST_PATHS=(tokio/tests/fs_file_join_error.rs)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cargo test -p tokio --test fs_file_join_error --features full

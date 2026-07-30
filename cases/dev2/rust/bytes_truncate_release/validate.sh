#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/tokio-rs/bytes"
GOLD_SHA="d5c8ad3227afe459c09f1d0d85455abf00f0381a"
TEST_PATHS=(tests/test_bytes.rs)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cargo test --test test_bytes

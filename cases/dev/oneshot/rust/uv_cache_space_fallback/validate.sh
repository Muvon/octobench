#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/astral-sh/uv"
GOLD_SHA="dca33f5e6799f2aefee52729732a839a3b358740"
TEST_PATHS=(crates/uv/tests/build/cache_clean.rs crates/uv/tests/build/cache_prune.rs)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

UV_INTERNAL__TEST_ALT_FS=/dev/shm \
  cargo test -p uv --test build physical_space_unsupported_fs -- --nocapture

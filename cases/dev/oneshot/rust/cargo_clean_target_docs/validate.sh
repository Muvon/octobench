#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/rust-lang/cargo"
GOLD_SHA="593ae3e482ae226d1f4533b29106f76e43649b70"
TEST_PATHS=(tests/testsuite/clean.rs tests/testsuite/clean_legacy_layout.rs)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cargo test --test testsuite clean_doc_target

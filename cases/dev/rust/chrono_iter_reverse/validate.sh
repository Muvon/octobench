#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/chronotope/chrono"
GOLD_SHA="7b6436f65e0c7ec2f9a7cdea88af1f3851a01f6f"
TEST_PATHS=(src/naive/date/tests.rs)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

# --lib only: the gold change also rewrites doc examples; doc tests at BASE
# state would false-fail a correct solution.
cargo test --lib iterator

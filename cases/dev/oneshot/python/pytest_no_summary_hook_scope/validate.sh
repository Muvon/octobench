#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pytest-dev/pytest"
GOLD_SHA="6f1b078537cf4ab14d0a7b29972c4e73f23a9011"
TEST_PATHS=(testing/test_terminal.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

# Covers the new hook-scope test plus the pre-existing --no-summary regression.
python -m pytest -q "${TEST_PATHS[@]}" -k "no_summary"

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pallets/click"
GOLD_SHA="7df2f82305f20f1611a9668b38d26933b648d807"
TEST_PATHS=(tests/test_shell_completion.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

python -m pytest -q "${TEST_PATHS[@]}"

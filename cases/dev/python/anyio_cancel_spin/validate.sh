#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/agronholm/anyio"
GOLD_SHA="dbba29d1ade7936f18fb71ba24aa92978673482a"
TEST_PATHS=(tests/test_taskgroups.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

python -m pytest -q "${TEST_PATHS[@]}"

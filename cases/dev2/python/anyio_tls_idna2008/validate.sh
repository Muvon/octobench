#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/agronholm/anyio"
GOLD_SHA="68f58915f82d9be8109ebbbd8f5d70577d43f2ce"
TEST_PATHS=(tests/streams/test_tls.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

python -m pytest -q tests/streams/test_tls.py

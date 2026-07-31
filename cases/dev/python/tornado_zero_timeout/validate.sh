#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/tornadoweb/tornado"
GOLD_SHA="18e15a5e0093b398a216fb9f85af69a3279b6e64"
TEST_PATHS=(tornado/test/queues_test.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

python -m pytest tornado/test/queues_test.py -q

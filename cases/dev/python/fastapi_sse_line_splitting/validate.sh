#!/usr/bin/env bash
set -euo pipefail

GOLD_SHA="0f3e7bd682a81488919227f2b5f1f7de1718ecdd"
TEST_PATH="tests/test_sse.py"

git remote add origin https://github.com/fastapi/fastapi 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATH}"
python -m pytest "${TEST_PATH}" -q

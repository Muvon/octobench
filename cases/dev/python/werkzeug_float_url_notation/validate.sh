#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pallets/werkzeug"
GOLD_SHA="a7e3ab2b42ab509148d2864e64a8f8378a638e7e"
TEST_PATHS=(tests/test_routing.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

python -m pytest -q "${TEST_PATHS[@]}"

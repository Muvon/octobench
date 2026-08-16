#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pallets/flask"
GOLD_SHA="d8eaaba824655046958d1a97f11780de460c3271"
TEST_PATHS=(tests/test_basic.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

python -m pytest -q -o addopts='' "${TEST_PATHS[@]}" -k method_route

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/python-attrs/attrs"
GOLD_SHA="97f8d175656bc03c373a1c9038048a4d312c307c"
TEST_PATHS=(tests/test_annotations.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

# Whole annotation suite: the forward-reference case plus every other spelling
# of ClassVar, so widening the check until it matches too much also fails.
python -m pytest -q "${TEST_PATHS[@]}"

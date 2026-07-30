#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pydantic/pydantic"
GOLD_SHA="60d4c4873e44d587c8d70d7a1c731f7361fe55eb"
TEST_PATHS=(tests/test_pipeline.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

python -m pytest -q -o addopts='' "${TEST_PATHS[@]}" -k test_json_schema

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pydantic/pydantic"
GOLD_SHA="cc13d1b8c978eaf78ed5308329cd41f03ecc3144"
TEST_PATHS=(tests/test_json_schema.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

python -m pytest -q -o addopts='' "${TEST_PATHS[@]}" -k bool_discriminated_union

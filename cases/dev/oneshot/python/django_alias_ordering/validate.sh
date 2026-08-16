#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/django/django"
GOLD_SHA="1a001208b0b9d79b15b27ca04d94f31f3d55d5ea"
TEST_PATHS=(tests/ordering/models.py tests/ordering/tests.py tests/composite_pk/test_order_by.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

.venv/bin/python tests/runtests.py ordering composite_pk --verbosity 1

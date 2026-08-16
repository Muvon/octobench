#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/aio-libs/aiohttp"
GOLD_SHA="26fde219b38ab0416f47b8165769d9df3f2ffece"
TEST_PATH="tests/test_http_parser.py"

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATH}"

make cythonize-nodeps > /dev/null
python -m pip install -q -e .
python -m pytest -q "${TEST_PATH}" \
  -k 'content_length_eof_while_paused or parse_length_payload_eof_completes_after_pause'

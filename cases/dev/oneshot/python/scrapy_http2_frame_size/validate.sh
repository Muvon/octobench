#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/scrapy/scrapy"
GOLD_SHA="a22523bfd3d4a9636ddf9d1834b925c19b579d71"
TEST_PATHS=(tests/test_http2_client_protocol.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

python -m pytest -q "${TEST_PATHS[@]}" -k GET_large_frames

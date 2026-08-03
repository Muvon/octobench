#!/usr/bin/env bash
set -euo pipefail

GOLD_SHA="f85031f61247dae1dcf19ca88cc057edba1534ee"
TEST_PATH="t/unit/events/test_events.py"

git remote add origin https://github.com/celery/celery 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATH}"
python -m pytest "${TEST_PATH}" -q

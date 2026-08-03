#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pinojs/pino-pretty"
GOLD_SHA="87ed39f620160e0e1ccb6edf36c2901f8d5de741"
TEST_PATHS=(lib/utils/prettify-error-log.test.js lib/utils/prettify-error.test.js lib/utils/prettify-message.test.js lib/utils/prettify-metadata.test.js lib/utils/prettify-object.test.js lib/utils/prettify-time.test.js)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

node --test "${TEST_PATHS[@]}"

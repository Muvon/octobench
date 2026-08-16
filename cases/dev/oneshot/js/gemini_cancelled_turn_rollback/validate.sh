#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/google-gemini/gemini-cli"
GOLD_SHA="783f6cb494aedf3e7276d02e76f32f63a27551a0"
TEST_PATHS=(packages/core/src/core/geminiChat.test.ts)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

npm run test --workspace @google/gemini-cli-core -- src/core/geminiChat.test.ts

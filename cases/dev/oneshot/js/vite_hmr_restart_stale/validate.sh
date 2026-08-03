#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/vitejs/vite"
GOLD_SHA="b1186c36d06bb94941c58e8272fc4acb8512c93b"
TEST_PATHS=(packages/vite/src/node/server/__tests__/hmr.spec.ts)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

pnpm --filter vite exec vitest run src/node/server/__tests__/hmr.spec.ts

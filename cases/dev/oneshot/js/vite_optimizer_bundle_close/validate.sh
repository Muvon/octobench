#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/vitejs/vite"
GOLD_SHA="8fb76752836f61224d3095b502fa237b478a06b2"
TEST_PATHS=(packages/vite/src/node/__tests__/optimizer/customExtensionBundleClose.spec.ts)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

pnpm --filter vite exec vitest run src/node/__tests__/optimizer/customExtensionBundleClose.spec.ts

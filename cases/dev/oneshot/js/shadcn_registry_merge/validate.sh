#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/shadcn-ui/ui"
GOLD_SHA="aef1cdca54e8da689351cdddf959342909e45e76"
TEST_PATHS=(packages/shadcn/src/commands/registry/add.test.ts packages/shadcn/src/registry/api.test.ts)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

pnpm --filter shadcn exec vitest run src/commands/registry/add.test.ts src/registry/api.test.ts

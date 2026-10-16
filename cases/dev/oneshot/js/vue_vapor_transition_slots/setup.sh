#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/vuejs/core"
BASE_SHA="829a53368a6cb9d45aaf388b62bde6d01213f794"

git config --global --add safe.directory "$(pwd)"
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

corepack enable
# Unit tests alias Vue packages to source and do not need a browser download.
PUPPETEER_SKIP_DOWNLOAD=1 pnpm install --frozen-lockfile --reporter=silent
pnpm exec vitest run --project unit \
  packages/reactivity/__tests__/effectScope.spec.ts --passWithNoTests=false

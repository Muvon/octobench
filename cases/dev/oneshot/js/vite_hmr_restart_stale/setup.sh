#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/vitejs/vite"
BASE_SHA="95a3cdab83e1125b03d2e8dd942fb6b64209e5fa"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

corepack enable
pnpm install --frozen-lockfile --reporter=silent
# vitest resolves `vite` to the workspace package; its dist/ must exist or
# every spec dies at import time with ERR_MODULE_NOT_FOUND.
pnpm --filter vite run build > /dev/null 2>&1

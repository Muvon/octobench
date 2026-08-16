#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/vitejs/vite"
BASE_SHA="a0cfcf72f8ef8bf0f2f11d553333b9bb31f1d316"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

corepack enable
pnpm install --frozen-lockfile --reporter=silent
pnpm --filter vite run build > /dev/null 2>&1

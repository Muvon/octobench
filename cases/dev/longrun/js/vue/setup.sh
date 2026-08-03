#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/vuejs/core"
BASE_SHA="7f46fd411b4e3f75ca755ee1318ea8e9aff43f56"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

corepack enable
# PUPPETEER_SKIP_DOWNLOAD: base allows puppeteer's postinstall Chrome download;
# unit tests never need it. No build step — vitest aliases @vue/* to sources.
PUPPETEER_SKIP_DOWNLOAD=1 pnpm install --frozen-lockfile --reporter=silent

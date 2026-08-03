#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/axios/axios"
BASE_SHA="712e02373f1c5ac72fdf5da16f04838338ba817e"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
npm ci --ignore-scripts --no-audit --no-fund --loglevel=error

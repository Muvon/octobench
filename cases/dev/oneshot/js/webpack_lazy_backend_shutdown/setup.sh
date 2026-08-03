#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/webpack/webpack"
BASE_SHA="508e10f54e0c581f6baf4189ee50b6f4ea2e57f5"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

corepack enable
yarn install --frozen-lockfile --ignore-scripts --non-interactive

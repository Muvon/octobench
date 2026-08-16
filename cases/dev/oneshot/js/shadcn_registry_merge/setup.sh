#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/shadcn-ui/ui"
BASE_SHA="03c45b822e60195796dfd3d2fcf7c223ff4ece86"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

corepack enable
pnpm install --frozen-lockfile --ignore-scripts --reporter=silent

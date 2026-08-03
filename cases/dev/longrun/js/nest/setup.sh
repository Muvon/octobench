#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nestjs/nest"
BASE_SHA="6dd6e979e033364523d96649236b7e481efdc551"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

# CI-equivalent install. Do NOT `npm run build`: it emits .js next to the .ts
# sources and copies packages into node_modules/@nestjs, shadowing live edits —
# mocha runs specs from .ts via ts-node + tsconfig-paths with no build.
npm install --legacy-peer-deps --no-audit --no-fund --loglevel=error

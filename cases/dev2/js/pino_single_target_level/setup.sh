#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pinojs/pino"
BASE_SHA="7b2fee8700cb4ecab0d55dbe831d60b60fc16929"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

npm install --no-audit --no-fund --loglevel=error

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pinojs/pino-pretty"
BASE_SHA="a93ed108418d64c089ba9474cc96685dc2e417f2"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

npm install --no-audit --no-fund --loglevel=error

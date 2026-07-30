#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nodejs/undici"
BASE_SHA="3c662a598cae8ea6dc5b605a2a0de0de11647437"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

npm ci --no-audit --no-fund --loglevel=error

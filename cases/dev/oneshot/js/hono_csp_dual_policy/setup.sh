#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/honojs/hono"
BASE_SHA="c85aead088659b98b8d05a1187a07d064e12ffe6"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

npm install --no-audit --no-fund --loglevel=error

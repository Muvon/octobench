#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/google-gemini/gemini-cli"
BASE_SHA="fa2f27aee0464412e4ac455a4221b01a775ff9bc"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

npm ci --ignore-scripts --no-audit --no-fund --loglevel=error
npm run generate > /dev/null
npm run build --workspace @google/gemini-cli-core > /dev/null

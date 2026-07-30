#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/eslint/eslint"
BASE_SHA="044a627fa3e28ee1410d515acc5378eb4b49f8ba"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

npm install --no-audit --no-fund --loglevel=error

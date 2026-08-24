#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/eslint/eslint"
BASE_SHA="a9e5961050676ef29dba9649dfcd7233d21760c7"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

npm install --no-audit --no-fund --loglevel=error

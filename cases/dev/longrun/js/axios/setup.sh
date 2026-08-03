#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/axios/axios"
BASE_SHA="ff60b43277c32a5b2f7589c917db16d8e043c0d4"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B v1.x
git remote remove origin

npm install --silent

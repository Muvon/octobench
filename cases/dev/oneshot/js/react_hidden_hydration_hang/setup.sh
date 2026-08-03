#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/facebook/react"
BASE_SHA="96fcba90138e9f1a73ee1cc4f79a653ec12fc3a9"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

corepack enable
yarn install --frozen-lockfile --non-interactive

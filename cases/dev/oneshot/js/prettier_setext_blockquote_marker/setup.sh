#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/prettier/prettier"
BASE_SHA="45a4a75ea639e69d35f885224818e6698561fc11"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

corepack enable > /dev/null 2>&1 || true
yarn install --immutable

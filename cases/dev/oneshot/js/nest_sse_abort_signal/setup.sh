#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nestjs/nest"
BASE_SHA="42f0cfdef7692fa57c9190a4ea9130920eb80ba5"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

npm install --legacy-peer-deps --ignore-scripts --no-audit --no-fund --loglevel=error

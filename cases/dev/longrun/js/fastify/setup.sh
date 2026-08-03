#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/fastify/fastify"
BASE_SHA="8b9c07b645a8156c23a1d2619267fc84ea879250"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

npm install --silent

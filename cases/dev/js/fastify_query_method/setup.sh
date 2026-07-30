#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/fastify/fastify"
BASE_SHA="de3752df84bb8dd35a8226bb467f05862f4da57c"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

npm install --no-audit --no-fund --loglevel=error

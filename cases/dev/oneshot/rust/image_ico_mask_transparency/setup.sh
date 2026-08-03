#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/image-rs/image"
BASE_SHA="86e7792285a05049e43f68a7fd55de66ca88e5ab"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cargo build --tests 2>/dev/null || true

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/chronotope/chrono"
BASE_SHA="7fa24eac9514db65eb8bddf7fadeca71b68e414a"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cargo test --lib --no-run -q

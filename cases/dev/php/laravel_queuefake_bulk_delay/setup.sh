#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/laravel/framework"
BASE_SHA="91eee4b8a7c4f4301700fa359de92898528bb917"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 13.x
git remote remove origin

composer install --no-interaction --no-progress --quiet

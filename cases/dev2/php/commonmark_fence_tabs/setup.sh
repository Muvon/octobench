#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/thephpleague/commonmark"
BASE_SHA="cfb11eca1dce491891141055b945724b25434c74"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 2.8
git remote remove origin

composer install --no-interaction --no-progress --quiet

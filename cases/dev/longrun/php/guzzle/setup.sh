#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/guzzle/guzzle"
BASE_SHA="74df5f7b7f1dc15fd9048475f43adf90f17d5b8c"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 8.0
git remote remove origin

composer install --no-interaction --no-progress --quiet --prefer-dist

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/guzzle/guzzle"
BASE_SHA="ecfbeb7a08fbbc5cfc0ab49ae56fcc71447160b5"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 8.0
git remote remove origin

composer install --no-interaction --no-progress --quiet --prefer-dist

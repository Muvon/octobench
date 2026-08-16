#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pestphp/pest"
BASE_SHA="a8d4770c0b1e7bc37d28f0b95aa5caaa01827d4d"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 5.x
git remote remove origin

php8.4 /usr/local/bin/composer install --no-interaction --no-progress --quiet

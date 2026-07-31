#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/composer/composer"
BASE_SHA="138899a081757ceb770bd53b1ca575244d8aed06"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

composer install --no-interaction --no-progress --quiet
vendor/bin/simple-phpunit --version

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/symfony/symfony"
BASE_SHA="e7f5b52df7bf719cbf379e7cdf7040e0cca32564"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 8.2
git remote remove origin

php8.4 /usr/local/bin/composer install --no-interaction --no-progress --quiet
SYMFONY_PHPUNIT_VERSION=13 php8.4 ./phpunit --version

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/doctrine/orm"
BASE_SHA="9738e13e32b133b1d779193bb463ff9ed94f2f8d"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 3.7.x
git remote remove origin

# Fully offline tests: phpunit.xml.dist pins pdo_sqlite + db_memory=true, so
# functional tests run on in-memory SQLite (php-sqlite3 is in the image).
composer install --no-interaction --no-progress --quiet --prefer-dist

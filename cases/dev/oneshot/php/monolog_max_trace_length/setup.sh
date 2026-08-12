#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/Seldaek/monolog"
BASE_SHA="b321dd6749f0bf7189444158a3ce785cc16d69b0"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# monolog's dev deps pull mongodb/mongodb (needs ext-mongodb, absent here); the
# graded tests do not touch it, so install regardless of platform extensions.
composer install --no-interaction --no-progress --quiet --ignore-platform-reqs
vendor/bin/phpunit --version

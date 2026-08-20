#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/laravel/framework"
BASE_SHA="faf45dd2b1549ff451993e9b20047ff0bf093033"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 13.x
git remote remove origin

# laravel 13.x requires php ^8.3; the image default is 8.2 and ships 8.4 beside
# it for exactly this. composer itself must run under 8.4 too, or it resolves
# against the wrong platform version.
# ext-gmp is pulled in by a laravel dependency and is not in the agent
# image; the validated behaviour does not use it.
php8.4 /usr/local/bin/composer install --no-interaction --no-progress --quiet --ignore-platform-req=ext-gmp

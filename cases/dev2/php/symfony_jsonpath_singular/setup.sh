#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/symfony/symfony"
BASE_SHA="64418e15e4e806178c39cded5362a6c06ea43331"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 7.4
git remote remove origin

composer install --no-interaction --no-progress --quiet
# First run downloads the pinned PHPUnit distribution (setup-time network).
SYMFONY_PHPUNIT_VERSION=11.5 php ./phpunit --version

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/cakephp/cakephp"
BASE_SHA="3971a307e0acc5aed8289daa14afb5b72ae0d634"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 5.x
git remote remove origin

composer install --no-interaction --no-progress --quiet --ignore-platform-reqs
curl --retry 5 --retry-all-errors -fsSL \
  https://phar.phpunit.de/phpunit-11.5.44.phar -o /tmp/phpunit-11.phar
chmod +x /tmp/phpunit-11.phar
/tmp/phpunit-11.phar --version

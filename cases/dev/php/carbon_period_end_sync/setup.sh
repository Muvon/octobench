#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/briannesbitt/Carbon"
BASE_SHA="3db26e52db996da1d720d74bbbc99c1300fc0160"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

# The reported behavior only exists on PHP >= 8.2 (native DatePeriod properties).
php -r 'exit(PHP_VERSION_ID < 80200 ? 1 : 0);'

composer install --no-interaction --no-progress --quiet

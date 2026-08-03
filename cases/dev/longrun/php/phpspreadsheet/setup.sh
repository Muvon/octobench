#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/PHPOffice/PhpSpreadsheet"
BASE_SHA="803293efb9d32dfdd357a0a8d48cbffbe420d25f"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

# ext-gd is required by root+dev deps but the agent image has no php-gd; none
# of the turns' tests touch GD (no chart rendering / image writing).
composer install --no-interaction --no-progress --quiet --prefer-dist --ignore-platform-req=ext-gd

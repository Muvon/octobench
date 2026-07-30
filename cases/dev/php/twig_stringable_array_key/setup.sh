#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/twigphp/Twig"
BASE_SHA="2fb736d03319099b4847f73b0bddb8b883408854"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 3.x
git remote remove origin

composer install --no-interaction --no-progress --quiet
# simple-phpunit downloads its phpunit distribution on first run (setup-time
# network) so validate stays offline-fast.
vendor/bin/simple-phpunit --version

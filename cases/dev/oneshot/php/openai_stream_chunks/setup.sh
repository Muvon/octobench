#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/openai-php/client"
BASE_SHA="9b84990f4b6fd9a7d4240c0aa91627e12fdbb719"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

composer install --no-interaction --no-progress --quiet

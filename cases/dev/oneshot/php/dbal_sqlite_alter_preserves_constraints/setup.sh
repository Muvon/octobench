#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/doctrine/dbal"
BASE_SHA="6d8aa68d21f903101b6632e76a40a8626e61c56a"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 4.4.x
git remote remove origin

composer install --no-interaction --no-progress --quiet

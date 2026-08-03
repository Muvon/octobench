#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/thephpleague/flysystem"
BASE_SHA="48ea21da9107519a161fc1cc03e19d1905d92cea"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 3.x
git remote remove origin

# require-dev lists exotic extensions (mongodb, ftp) unrelated to this case.
composer install --no-interaction --no-progress --quiet --ignore-platform-reqs

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/laravel/framework"
BASE_SHA="d400567edfff75bbaa0c942a906a5b71c996ffc6"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 13.x
git remote remove origin

apt-get update -qq
apt-get install -y --no-install-recommends php8.4-redis redis-server > /dev/null
rm -rf /var/lib/apt/lists/*
redis-server --daemonize yes
php8.4 -m | grep -qi '^redis$'
redis-cli ping | grep -q '^PONG$'

php8.4 /usr/local/bin/composer install \
  --no-interaction --no-progress --quiet --ignore-platform-req=ext-gmp

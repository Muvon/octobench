#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/symfony/symfony"
BASE_SHA="35781eed5a4b6a179606dbbd7714ef2fdab03317"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
# Branch name is load-bearing: composer derives self.version for the monorepo
# `replace` block from it; without `-B 7.4` resolution fails outright.
git checkout -q -B 7.4
git remote remove origin

composer install --no-interaction --no-progress --quiet

# The repo-root ./phpunit wrapper downloads its PHPUnit on first run — do it
# now while network is allowed (validate runs offline). It picks the version
# from the running PHP (8.2 -> 11.5); simple-phpunit's 9.6 default cannot read
# PHP attributes and breaks every #[DataProvider] test.
./phpunit --version > /dev/null 2>&1 || true

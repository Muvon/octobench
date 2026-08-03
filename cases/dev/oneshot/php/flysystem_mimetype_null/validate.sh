#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/thephpleague/flysystem"
GOLD_SHA="af41ef031c70b94664addbda174c5e9d4529ac21"
TEST_PATHS=(src/FilesystemTest.php)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

vendor/bin/phpunit src/FilesystemTest.php --no-coverage

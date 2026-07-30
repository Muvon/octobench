#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/symfony/symfony"
GOLD_SHA="b785a298870b3e421b24972a6eb7cc39c162b57a"
TEST_PATHS=(src/Symfony/Component/JsonPath/Tests/JsonCrawlerTest.php)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

SYMFONY_PHPUNIT_VERSION=11.5 php ./phpunit "${TEST_PATHS[@]}"

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/symfony/symfony"
GOLD_SHA="8346f69cec0bb8f64855bae77c1187ad19619138"
TEST_PATHS=(
  src/Symfony/Component/Console/Tests/Descriptor/AbstractDescriptorTestCase.php
  src/Symfony/Component/Console/Tests/Descriptor/TextDescriptorTest.php
)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

SYMFONY_PHPUNIT_VERSION=13 php8.4 ./phpunit src/Symfony/Component/Console/Tests/Descriptor/TextDescriptorTest.php

#!/usr/bin/env bash
set -euo pipefail

GOLD_SHA="950cbd2c4f15fd2a74049f67051b086347ae113f"
TEST_PATH="tests/TestCase/Http/Middleware/RateLimitMiddlewareTest.php"

git remote add origin https://github.com/cakephp/cakephp 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATH}"
php -d zend.assertions=1 /tmp/phpunit-11.phar --no-coverage "${TEST_PATH}"

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/cakephp/cakephp"
GOLD_SHA="209e4458570c6f3777e02214ed4c6c15b6f9c79c"
TEST_PATH="tests/TestCase/ORM/Query/QueryRegressionTest.php"

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATH}"

php -d zend.assertions=1 /tmp/phpunit-11.phar --no-coverage "${TEST_PATH}" \
  --filter 'testSubqueryStrategyOrderedByNonKeyColumn|testSubqueryStrategyOrderedByExpression|testSubqueryStrategyGroupsByOrderedColumns'

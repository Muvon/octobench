#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/doctrine/dbal"
GOLD_SHA="34b62998bf626326184bc25f58b39518d04928ce"
TEST_PATHS=(tests/Functional/Schema/SchemaManagerFunctionalTestCase.php)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# The executed suite file is restored too, so agent edits to it cannot change what runs.
git checkout -q "${GOLD_SHA}" -- tests/Functional/Schema/SQLiteSchemaManagerTest.php
# Restore the upstream PHPUnit harness so agent edits cannot bypass the tests.
git checkout -q "${GOLD_SHA}" -- tests/FunctionalTestCase.php phpunit.xml.dist
git -c safe.directory='*' clean -fdq -- tests
rm -f phpunit.xml

# phpunit.xml.dist runs against SQLite by default -> no database server needed.
vendor/bin/phpunit tests/Functional/Schema/SQLiteSchemaManagerTest.php

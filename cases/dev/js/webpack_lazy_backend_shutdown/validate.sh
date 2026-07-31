#!/usr/bin/env bash
set -euo pipefail

GOLD_SHA="a24f33283f5b073f2e0e845badd1ec469272702b"
TEST_PATH="test/LazyCompilationBackend.unittest.js"

git remote add origin https://github.com/webpack/webpack 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATH}"
yarn test:base "${TEST_PATH}" --runInBand

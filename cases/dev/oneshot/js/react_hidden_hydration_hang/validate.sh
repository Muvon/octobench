#!/usr/bin/env bash
set -euo pipefail

GOLD_SHA="9a81195bed0ded96e10a13f753dce05bee8cc97b"
TEST_ONE="packages/react-dom/src/__tests__/ReactDOMServerPartialHydration-test.internal.js"
TEST_TWO="packages/react-dom/src/__tests__/ReactDOMServerPartialHydrationActivity-test.internal.js"

git remote add origin https://github.com/facebook/react 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_ONE}" "${TEST_TWO}"
yarn test ReactDOMServerPartialHydration-test.internal --runInBand
yarn test ReactDOMServerPartialHydrationActivity-test.internal --runInBand

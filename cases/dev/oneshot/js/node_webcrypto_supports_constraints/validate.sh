#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nodejs/node"
GOLD_SHA="e1cdcec71899c3ae03df055aac02fb520d16e762"
TEST_PATHS=(
  test/fixtures/webcrypto/supports-level-2.mjs
  test/fixtures/webcrypto/supports-modern-algorithms.mjs
  test/fixtures/webcrypto/supports-secure-curves.mjs
  test/parallel/test-webcrypto-derivebits-hkdf.js
  test/parallel/test-webcrypto-keygen.js
  test/parallel/test-webcrypto-promise-prototype-pollution.mjs
  test/parallel/test-webcrypto-sign-verify-eddsa.js
  test/parallel/test-webcrypto-sign-verify-ml-dsa.js
  test/parallel/test-webcrypto-sign-verify-rsa.js
  test/parallel/test-webcrypto-supports.mjs
  test/parallel/test-webcrypto-util.js
)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

for test_path in "${TEST_PATHS[@]:3}"; do
  out/Release/node "${test_path}"
done

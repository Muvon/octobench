#!/usr/bin/env bash
set -euo pipefail

GOLD_SHA="7b7f4511a4f8395e67a1d8b0e97e840b0fa117eb"
TEST_ONE="rustls/src/client/test.rs"
TEST_TWO="rustls/src/msgs/handshake_test.rs"

git remote add origin https://github.com/rustls/rustls 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_ONE}" "${TEST_TWO}"
cargo test -p rustls --lib

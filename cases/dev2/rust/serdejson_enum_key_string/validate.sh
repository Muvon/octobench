#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/serde-rs/json"
GOLD_SHA="1a360b0a6c003912afc3503c834b0edd798bca28"
TEST_PATHS=(tests/regression/issue979.rs)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# automod enumerates tests/regression/ at compile time and cargo does not see
# the new file as a build input — force the test crate to recompile.
touch tests/regression.rs

cargo test --test regression issue979

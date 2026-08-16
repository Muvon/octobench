#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nushell/nushell"
GOLD_SHA="7d70a8fa3acc23e7895a6874582f95c6048baa47"
TEST_PATHS=(crates/nu-command/tests/commands/stor.rs)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cargo test -p nu-command --test tests -- stor_import_missing_file

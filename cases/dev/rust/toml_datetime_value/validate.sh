#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/toml-rs/toml"
GOLD_SHA="89f55411d47ee9fb349ab0704f287aa82aa12258"
TEST_PATHS=(crates/toml/tests/serde/general.rs crates/toml_edit/tests/serde/general.rs)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cargo test -p toml --test serde deserialize_datetime_from_value_issue_440
cargo test -p toml_edit --features serde --test serde deserialize_datetime_from_value_issue_440

#!/usr/bin/env bash
set -euo pipefail

GOLD_SHA="91d3b4c0bccf2234fc3ed19e605e2cd402f19437"
TEST_PATH="tokio/src/runtime/time_alt/tests.rs"

git remote add origin https://github.com/tokio-rs/tokio 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATH}"
export LOOM_MAX_PREEMPTIONS=3
RUSTFLAGS="--cfg tokio_unstable" \
  cargo test -p tokio --lib --features full insert_of_already_cancelled_entry_does_not_enter_wheel
RUSTFLAGS="--cfg loom --cfg tokio_unstable" \
  cargo test -p tokio --lib --features full cancel_races_with_insert

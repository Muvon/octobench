#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nushell/nushell"
GOLD_SHA="67edfb6eca0ac5b4c69d614d8e290b7134213b38"
TEST_PATHS=(
  crates/nu-command/tests/commands/mod.rs
  crates/nu-command/tests/commands/record/mod.rs
  crates/nu-command/tests/commands/record/apply.rs
  crates/nu-command/tests/commands/record/each.rs
  crates/nu-command/tests/commands/record/walk.rs
  crates/nu-command/tests/commands/record/where_.rs
)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Restore the untouched integration-test root so agent edits cannot replace the tests.
git checkout -q "${GOLD_SHA}" -- crates/nu-command/tests/main.rs crates/nu-test-support crates/testbins
git -c safe.directory='*' clean -fdq -- crates/nu-test-support crates/testbins
git -c safe.directory='*' clean -fdq -- crates/nu-command/tests

cargo build --locked --offline --bin nu
cargo build --locked --offline --manifest-path crates/testbins/Cargo.toml --bins
cargo test --locked --offline -p nu-command --test tests --no-run

RECORD_TEST_TIMEOUT=300s
if ! test_output="$(
  timeout --kill-after=10s "${RECORD_TEST_TIMEOUT}" \
    cargo test --locked --offline -p nu-command --test tests -- \
    'commands::record::' --nocapture 2>&1
)"; then
  printf '%s\n' "${test_output}"
  exit 1
fi
printf '%s\n' "${test_output}"

if ! grep -Fq 'test result: ok. 55 passed; 0 failed; 0 ignored;' <<<"${test_output}"; then
  echo "expected 55 selected record tests with none failed or ignored" >&2
  exit 1
fi

if ! grep -Fq 'record::where_::rejects_byte_stream_without_reading_it ... ok' <<<"${test_output}"; then
  echo "dependency-marked byte-stream test did not execute" >&2
  exit 1
fi

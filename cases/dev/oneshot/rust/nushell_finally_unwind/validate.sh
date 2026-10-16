#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nushell/nushell"
GOLD_SHA="9fc5f8d10e0f86e328021023ffc9a989e890578e"
TEST_PATHS=(crates/nu-command/tests/commands/try_.rs)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Restore the upstream integration-test roots so agent edits cannot replace the tests.
git checkout -q "${GOLD_SHA}" -- crates/nu-command/tests/main.rs crates/nu-command/tests/commands/mod.rs crates/nu-test-support crates/testbins
git -c safe.directory='*' clean -fdq -- crates/nu-test-support crates/testbins
git -c safe.directory='*' clean -fdq -- crates/nu-command/tests

cargo build --locked --offline --bin nu

test_names=(
  try_handlers_run_in_order
  error_in_try_with_only_finally_still_propagates_after_nested_finally
  nested_try_finally_value_is_seen_by_outer_catch
  exit_in_nested_try_skips_catch_but_runs_finally
)
expected_counts=(24 1 1 1)

for index in "${!test_names[@]}"; do
  test_name="${test_names[$index]}"
  if ! test_output="$(
    cargo test --locked --offline -p nu-command --test tests -- "${test_name}" 2>&1
  )"; then
    printf '%s\n' "${test_output}"
    exit 1
  fi
  printf '%s\n' "${test_output}"

  expected_count="${expected_counts[$index]}"
  if ! grep -Fq "test result: ok. ${expected_count} passed; 0 failed;" <<<"${test_output}"; then
    echo "expected ${expected_count} selected test(s) for ${test_name}" >&2
    exit 1
  fi
done

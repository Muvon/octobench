#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/bytecodealliance/wasmtime"
GOLD_SHA="894553615544793e912f79ac954baf358eab3b8b"
TEST_PATHS=(
  tests/misc_testsuite/component-model/async/exceptions.wast
  tests/misc_testsuite/component-model/exceptions.wast
)
REGRESSION_PATHS=(
  tests/misc_testsuite/many-results-with-exceptions.wast
  tests/misc_testsuite/stack-args-exceptions.wast
)

git fetch -q --depth 1 "${REPO_URL}" "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}" "${REGRESSION_PATHS[@]}"
# Restore the upstream WAST harness so agent edits cannot replace the selected trials.
git checkout -q "${GOLD_SHA}" -- tests/wast.rs crates/test-util/src/wast.rs crates/wast crates/test-util
git -c safe.directory='*' clean -fdq -- crates/wast crates/test-util
git -c safe.directory='*' clean -fdq -- tests crates/test-util/src

for test_path in "${TEST_PATHS[@]}" "${REGRESSION_PATHS[@]}"; do
  if ! test_output="$(
    cargo test --locked --offline -p wasmtime-cli --test wast -- \
      "${test_path}" --skip Winch/ --test-threads 1 --color never 2>&1
  )"; then
    printf '%s\n' "${test_output}"
    exit 1
  fi
  printf '%s\n' "${test_output}"

  # The harness creates one trial per compiler and file, not per WAST assertion.
  if ! grep -Eq '^test result: ok\. 1 passed; 0 failed; 0 ignored;' <<<"${test_output}"; then
    echo "expected one passing CraneliftNative WAST trial for ${test_path}" >&2
    exit 1
  fi
done

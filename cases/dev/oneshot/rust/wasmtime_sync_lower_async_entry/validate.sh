#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/bytecodealliance/wasmtime"
GOLD_SHA="65abe37529a6bca836efcac1dcb920d5c7890580"
TEST_PATHS=(
  tests/misc_testsuite/component-model/async/sync-lower-async-typed-entry-checks.wast
  tests/misc_testsuite/component-model/thread-transparency/reentrancy.wast
)

git fetch -q --depth 1 "${REPO_URL}" "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Restore the upstream WAST harness so agent edits cannot replace the selected trial.
git checkout -q "${GOLD_SHA}" -- tests/wast.rs crates/test-util/src/wast.rs crates/wast crates/test-util
git -c safe.directory='*' clean -fdq -- crates/wast crates/test-util
git -c safe.directory='*' clean -fdq -- tests crates/test-util/src

# The complete new file is audited; the cached reentrancy diff omits its body.
test_path="tests/misc_testsuite/component-model/async/sync-lower-async-typed-entry-checks.wast"
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

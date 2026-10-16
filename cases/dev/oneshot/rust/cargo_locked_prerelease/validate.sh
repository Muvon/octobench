#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/rust-lang/cargo"
GOLD_SHA="d83eabda2d0d8c17ea7bdc62136c020257f992c7"
TEST_PATHS=(
  tests/testsuite/precise_pre_release.rs
  tests/testsuite/cargo/z_help/stdout.term.svg
  crates/resolver-tests/src/lib.rs
  crates/resolver-tests/src/sat.rs
)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Restore the upstream integration-test roots so agent edits cannot replace the tests.
git checkout -q "${GOLD_SHA}" -- tests/testsuite/main.rs crates/cargo-test-support
git -c safe.directory='*' clean -fdq -- tests/testsuite

test_names=(
  update_pre_release
  pre_release_should_unmatched
  pre_release_should_matched
  pin_prereleases_in_separate_updates
  dont_select_prerelease_if_not_explicitly_pinned
  pin_prerelease_and_check
  pin_prerelease_and_check_without_zflag
  pin_prerelease_for_transitive_dep_and_check
  pin_prerelease_for_transitive_dep_of_patch_and_check
  pin_prerelease_for_shared_direct_transitive_dep_and_check
  pin_prerelease_for_shared_direct_transitive_dep_and_check_without_zflag
  pin_prerelease_and_update
)

for test_name in "${test_names[@]}"; do
  if ! test_output="$(
    cargo test --locked --offline --test testsuite \
      "precise_pre_release::${test_name}" -- --exact 2>&1
  )"; then
    printf '%s\n' "${test_output}"
    exit 1
  fi
  printf '%s\n' "${test_output}"

  if ! grep -Fq 'test result: ok. 1 passed; 0 failed;' <<<"${test_output}"; then
    echo "expected exactly one selected test for ${test_name}" >&2
    exit 1
  fi
done

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/duckdb/duckdb"
GOLD_SHA="6252031c70849a7ef8758a14012e2146762ddc25"
TEST_PATHS=(test/sql_export/sql_export_plan_sources.cpp)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Restore the upstream unit-test harness so agent edits cannot fabricate passing counts.
git checkout -q "${GOLD_SHA}" -- CMakeLists.txt test
git -c safe.directory='*' clean -fdq -- test

cmake --build build/debug --target unittest -j"$(nproc)"

selected_tests=(
  "Resolved subtree export preserves its original plan"
  "Resolved replacements take precedence over CTE producer shortcuts"
  "Aggregate recovery does not inspect a replaced projection"
  "Generated source names do not capture replacement catalog references"
  "Resolved subtree export rejects a plan with a detached child"
  "Window ordinality fusion respects replacement boundaries"
  "Replacement name reservation accepts a SELECT without a FROM node"
  "LIMIT reconstruction respects replacement boundaries"
)

for test_name in "${selected_tests[@]}"; do
  if ! test_output="$(build/debug/test/unittest "${test_name}" 2>&1)"; then
    printf '%s\n' "${test_output}"
    exit 1
  fi
  printf '%s\n' "${test_output}"

  if ! grep -Eq '(assertions:[[:space:]]*[1-9][0-9]*|[1-9][0-9]* assertions?)' <<<"${test_output}" ||
    ! grep -Eq '(test cases:[[:space:]]*[1-9][0-9]*|[1-9][0-9]* test cases?)' <<<"${test_output}"; then
    echo "${test_name} did not report non-zero assertion and test-case counts" >&2
    exit 1
  fi
done

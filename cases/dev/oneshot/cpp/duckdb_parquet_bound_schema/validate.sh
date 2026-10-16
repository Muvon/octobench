#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/duckdb/duckdb"
GOLD_SHA="87ef6e10b6f7b1325e9c66154feb54b06c2445ba"
TEST_PATHS=(
  test/parquet/parquet_bound_schema.test
  test/parquet/parquet_bound_schema_filter_mapping.test
  test/parquet/parquet_bound_schema_nested_roles.test
  test/parquet/parquet_bound_schema_plans.test
  test/parquet/parquet_bound_schema_roles.test
  test/parquet/parquet_bound_schema_roundtrip.test
  test/parquet/parquet_bound_schema_statistics.test
  test/parquet/parquet_bound_schema_validation.test
)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Restore the upstream unit-test harness so agent edits cannot fabricate passing counts.
git checkout -q "${GOLD_SHA}" -- CMakeLists.txt test
git -c safe.directory='*' clean -fdq -- test

cmake --build build/debug --target unittest -j"$(nproc)"

selected_tests=(
  test/parquet/parquet_bound_schema.test
  test/parquet/parquet_bound_schema_filter_mapping.test
  test/parquet/parquet_bound_schema_nested_roles.test
  test/parquet/parquet_bound_schema_roles.test
  test/parquet/parquet_bound_schema_roundtrip.test
  test/parquet/parquet_bound_schema_statistics.test
  test/parquet/parquet_bound_schema_validation.test
)

for test_path in "${selected_tests[@]}"; do
  if ! test_output="$(build/debug/test/unittest "${test_path}" 2>&1)"; then
    printf '%s\n' "${test_output}"
    exit 1
  fi
  printf '%s\n' "${test_output}"

  if ! grep -Eq '(assertions:[[:space:]]*[1-9][0-9]*|[1-9][0-9]* assertions?)' <<<"${test_output}" ||
    ! grep -Eq '(test cases:[[:space:]]*[1-9][0-9]*|[1-9][0-9]* test cases?)' <<<"${test_output}"; then
    echo "${test_path} did not report non-zero assertion and test-case counts" >&2
    exit 1
  fi
done

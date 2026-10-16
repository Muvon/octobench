#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pola-rs/polars"
GOLD_SHA="3def0ce97303a737bd8a2aedd01043c1aef13fca"
TEST_PATHS=(
  crates/polars-sql/tests/functions_meta.rs
  py-polars/tests/unit/functions/test_when_then.py
  py-polars/tests/unit/operations/test_gather.py
  py-polars/tests/unit/operations/test_group_by.py
  py-polars/tests/unit/operations/test_row_encoding.py
  py-polars/tests/unit/operations/test_statistics.py
  py-polars/tests/unit/sql/test_agg_semantics.py
  py-polars/tests/unit/sql/test_array.py
  py-polars/tests/unit/sql/test_filter_clause.py
  py-polars/tests/unit/sql/test_group_by.py
  py-polars/tests/unit/sql/test_subqueries.py
)

git fetch -q --depth 1 "${REPO_URL}" "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Includes conftests, SQL helpers, fixtures and Python/Rust assertion utilities.
# No gold production-source changes intersect these restored harness paths.
git checkout -q "${GOLD_SHA}" -- \
  py-polars/tests crates/polars-sql/tests \
  py-polars/pyproject.toml py-polars/src/polars/testing \
  crates/polars-python/src/testing crates/polars-testing
git -c safe.directory='*' clean -fdq -- \
  py-polars/tests crates/polars-sql/tests py-polars/src/polars/testing \
  crates/polars-python/src/testing crates/polars-testing

export RUSTUP_TOOLCHAIN=nightly-2026-09-01
export CARGO_BUILD_JOBS=6
export VIRTUAL_ENV=/opt/venv

maturin develop --manifest-path py-polars/runtime/polars-runtime-32/Cargo.toml --locked --offline
python - <<'PY'
from pathlib import Path
import duckdb
import polars
import polars._plr as native
import pyarrow

root = Path.cwd().resolve()
for module in (polars, native):
    path = Path(module.__file__).resolve()
    print(f"{module.__name__}: {path}")
    if not path.is_relative_to(root):
        raise SystemExit(f"Expected workspace module: {path}")
PY

report="$(mktemp)"
trap 'rm -f "${report}"' EXIT
cd py-polars
python -m pytest -q -c pyproject.toml --confcutdir=tests \
  -o addopts='--strict-config --strict-markers --import-mode=importlib' \
  --junitxml="${report}" \
  tests/unit/sql/test_agg_semantics.py::test_aggregate_of_constant \
  tests/unit/sql/test_agg_semantics.py::test_sum_of_constant_types \
  tests/unit/sql/test_agg_semantics.py::test_spread_of_non_finite_constant \
  tests/unit/sql/test_agg_semantics.py::test_sum_of_integer_literal \
  tests/unit/sql/test_filter_clause.py::test_filter_clause_misc_aggfuncs \
  tests/unit/sql/test_filter_clause.py::test_filter_clause_non_boolean_error \
  tests/unit/sql/test_group_by.py::test_having_on_group_key \
  tests/unit/sql/test_group_by.py::test_column_outside_aggregate_without_group_by_error \
  tests/unit/sql/test_group_by.py::test_aggregate_with_excluded_columns \
  tests/unit/sql/test_subqueries.py::test_scalar_subquery_in_aggregate \
  tests/unit/sql/test_subqueries.py::test_scalar_subquery_as_aggregate_parameter \
  tests/unit/functions/test_when_then.py::test_when_then_scalar_condition_with_cse_scalar_branch \
  tests/unit/operations/test_gather.py::test_gather_null_on_oob_group_by \
  tests/unit/operations/test_group_by.py::test_group_by_repeat_literal_on_empty \
  tests/unit/operations/test_statistics.py::test_cov_one_row

python - "${report}" <<'PY'
import sys
import xml.etree.ElementTree as ET

expected_tests = 107
cases = ET.parse(sys.argv[1]).findall(".//testcase")
if len(cases) != expected_tests or any(
    case.find(status) is not None
    for case in cases
    for status in ("failure", "error", "skipped")
):
    raise SystemExit(f"Expected {expected_tests} passing upstream tests without skips")
print(f"Validated {expected_tests} upstream tests without skips")
PY

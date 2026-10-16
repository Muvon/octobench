#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/python/mypy"
GOLD_SHA="b645e069c1e7f907205e6cc0eabea5d2b5beeefc"
TEST_PATHS=(
  mypy/test/testcmdline.py
  test-data/unit/check-bound.test
  test-data/unit/check-classes.test
  test-data/unit/check-columns.test
  test-data/unit/check-custom-plugin.test
  test-data/unit/check-errorcodes.test
  test-data/unit/check-functions.test
  test-data/unit/check-generics.test
  test-data/unit/check-incremental.test
  test-data/unit/check-inference.test
  test-data/unit/check-plugin-attrs.test
  test-data/unit/check-protocols.test
  test-data/unit/check-redefine2.test
  test-data/unit/check-selftype.test
  test-data/unit/cmdline.test
  test-data/unit/exportjson.test
)

git fetch -q --depth 1 "${REPO_URL}" "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Restore collectors, helpers, configuration, and all loaded test fixtures.
# Gold production changes are mypy/build.py and mypy/semanal.py; neither is restored.
git checkout -q "${GOLD_SHA}" -- conftest.py pyproject.toml mypy/test test-data
git -c safe.directory='*' clean -fdxq -- mypy/test test-data mypy/conftest.py

SELECTED_TESTS=(
  mypy/test/testcheck.py::TypeCheckSuite::check-inference.test::testInferAttributeInitializedToNoneAndAssignedClassBody
  mypy/test/testcheck.py::TypeCheckSuite::check-inference.test::testPartiallyInitializedVariableDoesNotEscapeScope2
  mypy/test/testcheck.py::TypeCheckSuite::check-inference.test::testGlobalInitializedToNoneSetFromFunction
  mypy/test/testcheck.py::TypeCheckSuite::check-inference.test::testGlobalInitializedToNoneSetFromMethod
  mypy/test/testcheck.py::TypeCheckSuite::check-inference.test::testPartialTypeErrorSpecialCase1
  mypy/test/testcheck.py::TypeCheckSuite::check-inference.test::testPartialTypeErrorSpecialCase3
  mypy/test/testcheck.py::TypeCheckSuite::check-inference.test::testNoCrashOnPartialMember
  mypy/test/testcheck.py::TypeCheckSuite::check-inference.test::testNoCrashOnPartialVariable2
  mypy/test/testcheck.py::TypeCheckSuite::check-inference.test::testLocalPartialTypesWithGlobalInitializedToNone4
  mypy/test/testcheck.py::TypeCheckSuite::check-inference.test::testLocalPartialTypesWithGlobalInitializedToNone5
  mypy/test/testcheck.py::TypeCheckSuite::check-inference.test::testPerFileNoLocalPartialTypesForcesSinglePhase_no_parallel
  mypy/test/testcheck.py::TypeCheckSuite::check-incremental.test::testNoCrashOnPartialLambdaInference_no_parallel
  mypy/test/testcheck.py::TypeCheckSuite::check-classes.test::testPartialNoneTypeClassMethod
  mypy/test/testcmdline.py::PythonCmdlineSuite::cmdline.test::testCodeModeInParallelMode
  mypy/test/testcmdline.py::PythonCmdlineSuite::cmdline.test::testCacheInvalidatedForNoLocalPartialTypesParallelVsSequential
)

if ! test_output="$(PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS='' \
  python -m pytest -q -c pyproject.toml -o addopts='' "${SELECTED_TESTS[@]}" 2>&1)"; then
  printf '%s\n' "${test_output}"
  exit 1
fi
printf '%s\n' "${test_output}"

if ! grep -Eq "(^|[^0-9])${#SELECTED_TESTS[@]} passed([,[:space:]]|$)" <<<"${test_output}"; then
  echo "pytest did not pass every selected upstream test" >&2
  exit 1
fi

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pydantic/pydantic"
GOLD_SHA="1c8a330acc3077e77da64e3672c7c875fb4c6eaa"
TEST_PATHS=(
  pydantic-core/tests/validators/test_deque.py
  pydantic-core/tests/serializers/test_deque.py
  pydantic-core/tests/serializers/test_any.py
  pydantic-core/tests/test_errors.py
  pydantic-core/tests/test_schema_functions.py
  tests/test_validators.py
  tests/types/test_deque.py
)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Restore the upstream Pytest harness so agent edits cannot replace the selected tests.
git checkout -q "${GOLD_SHA}" -- pydantic-core/tests/conftest.py pydantic-core/tests/serializers/test_dataclasses.py pydantic-core/tests/serializers/test_list_tuple.py tests/conftest.py
git -c safe.directory='*' clean -fdq -- pydantic-core/tests tests

VIRTUAL_ENV=/opt/venv \
  maturin develop --manifest-path pydantic-core/Cargo.toml --locked --offline

python -c 'from pathlib import Path; import pydantic, pydantic_core, pydantic_core._pydantic_core as native; root = Path.cwd().resolve(); paths = {"pydantic": Path(pydantic.__file__).resolve(), "pydantic_core": Path(pydantic_core.__file__).resolve(), "pydantic_core._pydantic_core": Path(native.__file__).resolve()}; print(*(f"{name}: {path}" for name, path in paths.items()), sep="\n"); assert all(path.is_relative_to(root) for path in paths.values()), paths'

run_pytest() {
  local test_output
  if ! test_output="$(python -m pytest -q -o addopts='' "$@" 2>&1)"; then
    printf '%s\n' "${test_output}"
    exit 1
  fi
  printf '%s\n' "${test_output}"

  if ! grep -Eq '(^|[^0-9])[1-9][0-9]* passed' <<<"${test_output}"; then
    echo "pytest completed without running a passing selected test" >&2
    exit 1
  fi
}

run_pytest \
  pydantic-core/tests/validators/test_deque.py \
  pydantic-core/tests/serializers/test_deque.py \
  pydantic-core/tests/serializers/test_any.py::test_deque \
  pydantic-core/tests/serializers/test_any.py::test_deque_subclass \
  --deselect=pydantic-core/tests/validators/test_deque.py::test_repr \
  --deselect=tests/validators/test_deque.py::test_repr

run_pytest \
  tests/types/test_deque.py::test_deque_strict_fails \
  tests/types/test_deque.py::test_deque_constraints_core_schema \
  tests/types/test_deque.py::test_deque_constraints_json_schema \
  tests/types/test_deque.py::test_deque_maxlen_preserved_with_constraints \
  tests/types/test_deque.py::test_deque_serialization

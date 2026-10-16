#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/python-poetry/poetry"
GOLD_SHA="62018d105562e1365bf79607edcc29ed794e4635"
TEST_PATHS=(tests/console/commands/test_show.py)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Restore the upstream Pytest harness so agent edits cannot bypass the tests.
git checkout -q "${GOLD_SHA}" -- tests/conftest.py tests/console/conftest.py tests/console/commands/conftest.py tests/helpers.py
git -c safe.directory='*' clean -fdq -- tests

# -p no:randomly keeps ordering deterministic if pytest-randomly is installed.
# -o addopts='' drops poetry's pyproject addopts (demands pytest-xdist's -n).
python -m pytest -q -o addopts='' "${TEST_PATHS[@]}" -k outdated -p no:randomly

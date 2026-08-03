#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pytest-dev/pytest"
BASE_SHA="35f21fdcfc9b5817a2aafc449dc5cff5aba83725"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# setuptools_scm needs a version source; the shallow no-tag checkout has none.
export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PYTEST=9.0.0.dev0
python -m pip install -q -e .
# testing/python/metafunc.py imports hypothesis; the other selected test files
# need only stdlib + _pytest internals (full [dev] extra is unnecessary).
python -m pip install -q hypothesis

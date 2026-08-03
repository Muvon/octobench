#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pytest-dev/pytest"
BASE_SHA="85003621822f9c10063940068ccacc9c12b8c73f"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# setuptools_scm has no version source in a shallow no-tag checkout; without a
# pretend version pytest installs as 0.1.dev and its own pyproject minversion
# check rejects it at collection time.
export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PYTEST=9.0.0.dev0
pip install -q -e .

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/python-poetry/poetry"
BASE_SHA="3a95c37c5d5ec600556f519e60e4340f35bbcac1"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# Runtime deps come from the project itself (poetry-core is a git dependency,
# so this step needs the network); the rest is poetry's own "test" group.
pip install -q -e .
pip install -q pytest pytest-mock deepdiff responses jaraco-classes

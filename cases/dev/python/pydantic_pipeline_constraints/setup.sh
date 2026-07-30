#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pydantic/pydantic"
BASE_SHA="d0ffa0951e47fd7349032e4b2ea9a54dc28fd435"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

pip install -q -e .
pip install -q pytest pytz jsonschema

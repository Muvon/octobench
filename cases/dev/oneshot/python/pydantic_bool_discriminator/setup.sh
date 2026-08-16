#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pydantic/pydantic"
BASE_SHA="52fbbfa1dc14a9b1fc40a1e246a3cbf2ce4987d1"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

python -m pip install -q -e .
python -m pip install -q pytest dirty-equals pytest-run-parallel jsonschema

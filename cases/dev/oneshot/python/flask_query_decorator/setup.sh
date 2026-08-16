#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pallets/flask"
BASE_SHA="3596b1ab61cea85edb8970e83ff61daa073facf8"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

python -m pip install -q -e .
python -m pip install -q pytest

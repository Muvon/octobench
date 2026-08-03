#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/celery/celery"
BASE_SHA="dd7c23862eb08a2cfde7da6926f28410b699c077"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

pip install -q -e .
pip install -q pytest pytest-subtests pytest-timeout pytest-click pytest-order

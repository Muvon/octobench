#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/python-attrs/attrs"
BASE_SHA="6851ab593cd25f3c14393e9355d57d22bec2a074"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

export SETUPTOOLS_SCM_PRETEND_VERSION=26.1.0
pip install -q -e .
pip install -q "pytest>=8" hypothesis

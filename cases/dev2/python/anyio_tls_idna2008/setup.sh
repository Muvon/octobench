#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/agronholm/anyio"
BASE_SHA="eb562e6462ee46b1904e50b02ce00a858cdeb200"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

export SETUPTOOLS_SCM_PRETEND_VERSION=4.15.0
pip install -q -e .
pip install -q "pytest>=9" pytest-mock pytest-timeout trustme trio psutil

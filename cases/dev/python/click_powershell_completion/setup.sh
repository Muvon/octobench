#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pallets/click"
BASE_SHA="b551fe85714c906565303fae98136d7c72b252ea"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

pip install -q -e . pytest

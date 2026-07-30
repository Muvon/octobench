#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pallets/werkzeug"
BASE_SHA="b97e13cc74d8a45dca260d4037edd7d1f5094042"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

pip install -q -e . pytest ephemeral-port-reserve

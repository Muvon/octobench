#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nushell/nushell"
BASE_SHA="faa6c11a792df6a1feeffdcb0d5d5188a802fb90"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cargo test -p nu-command --test tests --no-run

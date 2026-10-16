#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/rust-lang/cargo"
BASE_SHA="8814ead110e36ed8fdcf1fdd4009baf82bd78523"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

cargo test --locked --test testsuite --no-run

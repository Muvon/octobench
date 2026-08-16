#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/tokio-rs/tokio"
BASE_SHA="ddc60948ab7823e344ca766afbc8c7f5db896e6d"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

cargo test -p tokio --tests --features full --no-run

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/serde-rs/json"
BASE_SHA="5d30df60e916e9b8fc46c74794007ff271fdfbbf"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

cargo test --test regression --no-run -q

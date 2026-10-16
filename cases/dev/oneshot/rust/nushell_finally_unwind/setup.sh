#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nushell/nushell"
BASE_SHA="394a9ec849e07f32d40f2f368573f59552c16e8f"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cargo build --locked --bin nu
cargo test --locked -p nu-command --test tests --no-run

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nushell/nushell"
BASE_SHA="145a0609c6050802bda2a6ae786fa912bc7bcc07"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cargo build --locked --bin nu
cargo build --locked --manifest-path crates/testbins/Cargo.toml --bins
cargo test --locked -p nu-command --test tests --no-run

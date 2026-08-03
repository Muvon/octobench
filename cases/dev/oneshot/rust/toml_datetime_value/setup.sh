#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/toml-rs/toml"
BASE_SHA="4ec099fed591a172f82007cb2f9d605985bbecee"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cargo test -p toml --test serde --no-run -q
cargo test -p toml_edit --features serde --test serde --no-run -q

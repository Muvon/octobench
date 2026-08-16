#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/astral-sh/uv"
BASE_SHA="3a76e496e36783371a6d91a8f4834478964d36ca"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cargo test -p uv --test build --no-run
# uv's integration-test context requires a managed 3.12 interpreter.
cargo run --quiet -- python install 3.12

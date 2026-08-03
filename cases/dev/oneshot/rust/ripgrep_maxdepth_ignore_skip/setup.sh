#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/BurntSushi/ripgrep"
BASE_SHA="dffd776a737dc19a48b758dd6a621de113794121"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

cargo test -p ignore --lib --no-run -q

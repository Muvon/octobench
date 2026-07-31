#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/redis/redis"
BASE_SHA="ba99faa230643931f91d2d5d68a0393e25fa07f5"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B unstable
git remote remove origin

make -j"$(nproc)"

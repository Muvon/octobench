#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/python/cpython"
BASE_SHA="a74280e6696125acb7628facc577d0f975c4d69e"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

./configure --with-pydebug --without-ensurepip > /dev/null
make -j"$(nproc)" > /dev/null
./python -c 'import asyncio, _asyncio'

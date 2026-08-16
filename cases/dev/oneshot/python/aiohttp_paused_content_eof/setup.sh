#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/aio-libs/aiohttp"
BASE_SHA="6264834e7023aadd85646fd79637942b9edbe22b"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git submodule update --init --depth 1
git remote remove origin

python -m pip install -q -U pip setuptools
make generate-llhttp > /dev/null
make cythonize > /dev/null
python -m pip install -q -e .
python -m pip install -q -r requirements/test.in -c requirements/test.txt

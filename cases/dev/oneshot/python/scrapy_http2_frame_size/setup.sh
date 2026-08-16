#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/scrapy/scrapy"
BASE_SHA="f975e921591366502ea8e05a10559a300b5fce4e"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

python -m pip install -q -e '.[twisted-http2]'
python -m pip install -q pytest pytest-asyncio pytest-twisted pytest-cov

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/tornadoweb/tornado"
BASE_SHA="affd7939a7985d3eef5b7bec39697287007a5328"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

TORNADO_EXTENSION=0 pip install -q -e .
pip install -q pytest

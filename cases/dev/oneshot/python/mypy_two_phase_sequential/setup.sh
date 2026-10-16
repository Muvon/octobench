#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/python/mypy"
BASE_SHA="5a06937f4607a03c4f2201f3aa9b7da99ec32402"

git config --global --add safe.directory "$(pwd)"
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

# GOLD requires fixed dependency versions.
awk '
  /^[[:space:]]*(#|$)/ { next }
  !/^[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+([[:space:]]|$)/ {
    print "Unpinned dependency in test-requirements.txt: " $0 > "/dev/stderr"
    invalid = 1
  }
  END { exit invalid }
' test-requirements.txt
python -m pip install -q --no-deps -r test-requirements.txt
MYPY_USE_MYPYC=0 python -m pip install -q --no-deps --no-build-isolation -e .
python -m pip check

python -m compileall -q -x '(^|/)(test|typeshed)(/|$)' mypy
python -m mypy --version

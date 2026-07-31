#!/usr/bin/env bash
set -euo pipefail

GOLD_SHA="d3315247fa1cf9ce079eb7b6e77a7d06ac643b2a"
TEST_PATH="tests/unit/acl-v2.tcl"

git remote add origin https://github.com/redis/redis 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATH}"
make -j"$(nproc)"
./runtest --single unit/acl-v2

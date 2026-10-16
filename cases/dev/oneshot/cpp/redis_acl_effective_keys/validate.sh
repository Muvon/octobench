#!/usr/bin/env bash
set -euo pipefail

GOLD_SHA="d3315247fa1cf9ce079eb7b6e77a7d06ac643b2a"
TEST_PATH="tests/unit/acl-v2.tcl"

git remote add origin https://github.com/redis/redis 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATH}"
# Restore the upstream Tcl harness so agent edits cannot bypass the test.
git checkout -q "${GOLD_SHA}" -- runtest tests/test_helper.tcl tests/support
git -c safe.directory='*' clean -fdq -- tests/support
make -j"$(nproc)"
./runtest --single unit/acl-v2

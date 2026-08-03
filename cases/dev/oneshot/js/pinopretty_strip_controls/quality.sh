#!/usr/bin/env bash
set -euo pipefail
find lib -name '*.js' ! -name '*.test.js' -print0 | xargs -0 -n50 node --check
echo "node --check OK"

#!/usr/bin/env bash
set -euo pipefail
cmake --build build --target std-test -j"$(nproc)"

#!/usr/bin/env bash
set -euo pipefail
cmake --build build --target libgit2_tests -j"$(nproc)"

#!/usr/bin/env bash
set -euo pipefail
cmake --build build --target yaml-cpp-tests -j"$(nproc)"

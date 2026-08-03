#!/usr/bin/env bash
set -euo pipefail
cmake --build build --target httplib -j"$(nproc)"

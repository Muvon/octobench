#!/usr/bin/env bash
set -euo pipefail
cmake --build build --target big_integer_tests ondemand_number_tests -j"$(nproc)"

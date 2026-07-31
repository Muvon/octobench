#!/usr/bin/env bash
set -euo pipefail

make -j"$(nproc)"

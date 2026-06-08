#!/usr/bin/env bash
set -euo pipefail

# Ground-truth gate: the tests must pass. Non-zero exit hard-fails the case.
python3 test_add.py

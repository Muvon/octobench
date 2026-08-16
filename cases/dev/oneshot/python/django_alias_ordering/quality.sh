#!/usr/bin/env bash
set -euo pipefail
.venv/bin/python -m compileall -q django/

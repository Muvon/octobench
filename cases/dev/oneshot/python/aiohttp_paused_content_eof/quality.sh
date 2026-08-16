#!/usr/bin/env bash
set -euo pipefail
make cythonize-nodeps > /dev/null
python -m pip install -q -e .
python -m compileall -q aiohttp/

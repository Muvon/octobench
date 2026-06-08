#!/usr/bin/env bash
set -euo pipefail

# Lightweight quality signal fed to the judge: add.py must still parse.
python3 -c "import ast; ast.parse(open('add.py').read()); print('add.py: syntax ok')"

#!/usr/bin/env bash
set -euo pipefail
find src/Illuminate/Http -name '*.php' -print0 | xargs -0 -n1 php8.4 -l > /dev/null

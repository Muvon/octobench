#!/usr/bin/env bash
set -euo pipefail
find src/Illuminate/Support -name '*.php' -print0 | xargs -0 -n50 php -l > /dev/null
echo "php -l OK"

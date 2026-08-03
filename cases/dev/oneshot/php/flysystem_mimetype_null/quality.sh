#!/usr/bin/env bash
set -euo pipefail
find src -name '*.php' ! -name '*Test.php' -print0 | xargs -0 -n50 php -l > /dev/null
echo "php -l OK"

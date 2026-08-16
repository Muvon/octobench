#!/usr/bin/env bash
set -euo pipefail
find src/Symfony/Component/Console -name '*.php' -print0 | xargs -0 -n50 php8.4 -l > /dev/null
echo "php8.4 -l OK"

#!/usr/bin/env bash
set -euo pipefail

php -l src/Http/Middleware/RateLimitMiddleware.php

#!/usr/bin/env bash
set -euo pipefail

php -l src/Composer/Advisory/Auditor.php
php -l src/Composer/DependencyResolver/Pool.php

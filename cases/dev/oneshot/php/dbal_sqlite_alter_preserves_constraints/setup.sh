#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/doctrine/dbal"
BASE_SHA="6d8aa68d21f903101b6632e76a40a8626e61c56a"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 4.4.x
git remote remove origin

# Strip dev-only lint/style tools blocked by Composer security advisories
# (PKSA-rdkp-vv9z-mjkg on squizlabs/php_codesniffer 4.0.1). These are not
# needed to run tests; phpunit and runtime deps install cleanly without them.
python3 -c "
import json
with open(\"composer.json\") as f:
    d = json.load(f)
dev = d.get(\"require-dev\", {})
for pkg in [\"squizlabs/php_codesniffer\", \"doctrine/coding-standard\", \"slevomat/coding-standard\"]:
    dev.pop(pkg, None)
d[\"require-dev\"] = dev
with open(\"composer.json\", \"w\") as f:
    json.dump(d, f, indent=4)
    f.write(\"\\n\")
"

composer install --no-interaction --no-progress --quiet

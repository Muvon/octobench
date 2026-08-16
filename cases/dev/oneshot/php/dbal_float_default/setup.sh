#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/doctrine/dbal"
BASE_SHA="05c991939825430e5a2b0aa621956ee68500564d"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B 4.4.x
git remote remove origin

# Dev-only coding-standard packages are blocked by Composer advisories in the
# base lock; they are not needed for the functional SQLite test.
python3 -c '
import json
with open("composer.json") as handle:
    data = json.load(handle)
dev = data.get("require-dev", {})
for package in ("squizlabs/php_codesniffer", "doctrine/coding-standard", "slevomat/coding-standard"):
    dev.pop(package, None)
data["require-dev"] = dev
with open("composer.json", "w") as handle:
    json.dump(data, handle, indent=4)
    handle.write("\n")
'

composer install --no-interaction --no-progress --quiet

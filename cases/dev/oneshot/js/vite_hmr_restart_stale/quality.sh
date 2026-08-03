#!/usr/bin/env bash
set -euo pipefail
pnpm --filter vite exec tsc --noEmit -p tsconfig.json

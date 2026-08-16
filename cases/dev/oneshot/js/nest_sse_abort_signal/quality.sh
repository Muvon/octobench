#!/usr/bin/env bash
set -euo pipefail
npx eslint packages/common/decorators/http packages/core/router packages/core/interceptors --max-warnings 0

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/nestjs/nest"
GOLD_SHA="b2e7fb5e763a3282c7b924a39e6adb373df7ea63"
TEST_PATHS=(
  packages/core/test/interceptors/interceptors-consumer.spec.ts
  integration/nest-application/sse/e2e/express.spec.ts
  integration/nest-application/sse/e2e/fastify.spec.ts
  integration/nest-application/sse/e2e/utils.ts
  integration/nest-application/sse/src/app.controller.ts
)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

node --loader ts-node/esm ./node_modules/mocha/bin/mocha.js \
  packages/core/test/interceptors/interceptors-consumer.spec.ts \
  integration/nest-application/sse/e2e/express.spec.ts \
  integration/nest-application/sse/e2e/fastify.spec.ts

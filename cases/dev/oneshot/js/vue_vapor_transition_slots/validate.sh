#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/vuejs/core"
GOLD_SHA="e656425ebff4724776a93c66c0113a902e91c200"
TEST_PATHS=(
  packages/runtime-vapor/__tests__/components/Transition.spec.ts
  packages/runtime-vapor/__tests__/hydration/interopTransition.spec.ts
  packages/runtime-vapor/__tests__/vdomInteropTransition.spec.ts
)

git fetch -q --depth 1 "${REPO_URL}" "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

# Restore the whole upstream test/support trees, including transitive helpers.
# No gold production change intersects these paths; see plan.md for exceptions.
gold_paths="$(git ls-tree -r --name-only "${GOLD_SHA}")"
support_paths=()
while IFS= read -r path; do
  case "${path}" in
    */__tests__/*|scripts/*|packages/runtime-test/*|package.json|*/package.json|\
    vitest*|*/vitest*|*.config.*|tsconfig*|*/tsconfig*|\
    pnpm-lock.yaml|pnpm-workspace.yaml|.npmrc|packages/global.d.ts|env.d.ts)
      support_paths+=("${path}")
      ;;
  esac
done <<<"${gold_paths}"
git checkout -q "${GOLD_SHA}" -- "${support_paths[@]}"
for test_dir in packages/*/__tests__ scripts packages/runtime-test; do
  git -c safe.directory='*' clean -fdq -- "${test_dir}"
done

run_vitest() {
  local expected_count="$1"
  local test_output
  shift
  if ! test_output="$(
    NO_COLOR=1 FORCE_COLOR=0 pnpm exec vitest run --project unit-jsdom \
      --reporter=default --passWithNoTests=false "$@" 2>&1
  )"; then
    printf '%s\n' "${test_output}"
    exit 1
  fi
  printf '%s\n' "${test_output}"
  if ! grep -Eq "^[[:space:]]*Tests[[:space:]]+${expected_count} passed([[:space:]]|$)" <<<"${test_output}"; then
    echo "expected ${expected_count} passing selected tests" >&2
    exit 1
  fi
}

run_vitest 30 packages/runtime-vapor/__tests__/vdomInteropTransition.spec.ts \
  -t '^(?!.*in-out switch between the slot and a vdom sibling)'
run_vitest 4 packages/runtime-vapor/__tests__/hydration/interopTransition.spec.ts
run_vitest 1 packages/runtime-vapor/__tests__/components/Transition.spec.ts \
  -t 'slot content rendered behind a fallback enters and leaves$'

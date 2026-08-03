#!/usr/bin/env bash
set -euo pipefail

yarn prettier-check packages/react-reconciler/src/ReactFiberBeginWork.js

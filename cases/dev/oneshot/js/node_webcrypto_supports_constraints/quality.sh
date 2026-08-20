#!/usr/bin/env bash
set -euo pipefail
out/Release/node --check lib/internal/crypto/hkdf.js
out/Release/node --check lib/internal/crypto/rsa.js
out/Release/node --check lib/internal/crypto/util.js
out/Release/node --check lib/internal/crypto/webcrypto.js
out/Release/node --check lib/internal/crypto/webidl.js

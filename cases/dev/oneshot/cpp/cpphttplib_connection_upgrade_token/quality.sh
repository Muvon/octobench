#!/usr/bin/env bash
set -euo pipefail
g++ -fsyntax-only -std=c++17 -x c++ httplib.h

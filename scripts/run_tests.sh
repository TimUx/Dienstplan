#!/usr/bin/env bash
# Run the default CI test gate from the repo root (no slow OR-Tools jobs).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 -m pytest -m "not slow" tests/ "$@"

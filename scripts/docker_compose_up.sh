#!/bin/bash
# Run docker compose up --build with a writable TMPDIR to avoid
# "can't access os.tempDir ... permission denied" on macOS.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
mkdir -p "$HOME/tmp/docker-build"
export TMPDIR="${TMPDIR:-$HOME/tmp/docker-build}"
cd "$PROJECT_ROOT"
exec docker compose up --build "$@"

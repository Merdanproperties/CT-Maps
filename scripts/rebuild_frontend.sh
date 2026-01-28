#!/bin/bash
# Rebuild and restart the frontend container so it picks up code changes.
# Use after editing frontend files when running with Docker.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
mkdir -p "$HOME/tmp/docker-build"
export TMPDIR="${TMPDIR:-$HOME/tmp/docker-build}"
cd "$PROJECT_ROOT"
exec docker compose up -d --build frontend "$@"

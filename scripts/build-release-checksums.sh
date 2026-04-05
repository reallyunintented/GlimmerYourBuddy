#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FILES=(
  LICENSE
  README.md
  SECURITY.md
  install.sh
  glimmer-claude
  glimmer-log
  glimmer-mcp
  glimmer-session.py
  glimmer-ui
  glimmer-watcher.py
  ui/index.html
  ui/app.js
  ui/styles.css
)

if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${FILES[@]}"
    exit 0
fi

if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${FILES[@]}"
    exit 0
fi

echo "Error: sha256sum or shasum is required." >&2
exit 1

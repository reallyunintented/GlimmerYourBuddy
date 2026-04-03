#!/usr/bin/env bash
#
# Glimmer install script — installs scripts into ~/.local/bin
#

set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
SHARE_DIR="${HOME}/.local/share/glimmer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="${GLIMMER_BASE_URL:-https://raw.githubusercontent.com/reallyunintented/GlimmerYourBuddy/main}"
SCRIPTS=(glimmer-claude glimmer-log glimmer-watcher.py glimmer-session.py glimmer-ui)
ASSETS=(ui/index.html ui/app.js ui/styles.css)

fetch_script() {
    local script="$1"

    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "${BASE_URL}/${script}"
        return
    fi

    if command -v wget >/dev/null 2>&1; then
        wget -qO- "${BASE_URL}/${script}"
        return
    fi

    echo "Error: install requires curl or wget." >&2
    exit 1
}

install_script() {
    local script="$1"
    local target="$BIN_DIR/$script"

    if [ -f "$SCRIPT_DIR/$script" ]; then
        cp "$SCRIPT_DIR/$script" "$target"
    else
        local tmp_file
        tmp_file="$(mktemp)"
        fetch_script "$script" > "$tmp_file"
        mv "$tmp_file" "$target"
    fi

    chmod +x "$target"
    echo "Installed $script"
}

install_asset() {
    local asset="$1"
    local target="$SHARE_DIR/$asset"

    mkdir -p "$(dirname "$target")"
    if [ -f "$SCRIPT_DIR/$asset" ]; then
        cp "$SCRIPT_DIR/$asset" "$target"
    else
        local tmp_file
        tmp_file="$(mktemp)"
        fetch_script "$asset" > "$tmp_file"
        mv "$tmp_file" "$target"
    fi

    echo "Installed $asset"
}

mkdir -p "$BIN_DIR"
mkdir -p "$SHARE_DIR"

for script in "${SCRIPTS[@]}"; do
    install_script "$script"
done

for asset in "${ASSETS[@]}"; do
    install_asset "$asset"
done

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "~/.local/bin is not in your PATH"
    echo "Add this to ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo ""
echo "Glimmer installed."
echo ""
echo "Next: Run 'glimmer-claude' instead of 'claude' to start capturing."
echo "View bubbles with: glimmer-log"
echo "Browse them with: glimmer-ui"

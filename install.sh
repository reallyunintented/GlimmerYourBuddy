#!/usr/bin/env bash
#
# Glimmer install script — copies scripts to ~/.local/bin
#

set -e

BIN_DIR="${HOME}/.local/bin"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create bin dir if needed
mkdir -p "$BIN_DIR"

# Copy scripts
for script in glimmer-claude glimmer-log glimmer-watcher.py; do
    if [ -f "$REPO_DIR/$script" ]; then
        cp "$REPO_DIR/$script" "$BIN_DIR/$script"
        chmod +x "$BIN_DIR/$script"
        echo "✓ Installed $script"
    fi
done

# Check if ~/.local/bin is in PATH
if ! echo "$PATH" | grep -q "$BIN_DIR"; then
    echo ""
    echo "⚠ ~/.local/bin is not in your PATH"
    echo "Add this to ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo ""
echo "✓ Glimmer installed!"
echo ""
echo "Next: Run 'glimmer-claude' instead of 'claude' to start capturing."
echo "View bubbles with: glimmer-log"

#!/usr/bin/env bash
#
# Glimmer install script — installs scripts into ~/.local/bin
#

set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
SHARE_DIR="${HOME}/.local/share/glimmer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_SLUG="${GLIMMER_REPO:-reallyunintented/GlimmerYourBuddy}"
REF="${GLIMMER_REF:-main}"
BASE_URL="${GLIMMER_BASE_URL:-https://raw.githubusercontent.com/${REPO_SLUG}/${REF}}"
SCRIPTS=(glimmer-claude glimmer-log glimmer-watcher.py glimmer-session.py glimmer-ui)
ASSETS=(ui/index.html ui/app.js ui/styles.css)
REMOTE_WARNING_SHOWN=0

warn_mutable_remote_install() {
    if [ "$REMOTE_WARNING_SHOWN" -eq 1 ]; then
        return
    fi

    if [ -n "${GLIMMER_BASE_URL:-}" ] || [ "$REF" != "main" ]; then
        REMOTE_WARNING_SHOWN=1
        return
    fi

    cat >&2 <<'EOF'
Warning: remote install is using the mutable 'main' branch.
Prefer a pinned commit for remote installs:
  GLIMMER_REF=<commit> bash install.sh
or clone the repo and run ./install.sh locally after inspection.
For the strongest path, install from a tagged release after verifying
SHA256SUMS.txt with the published Sigstore signature and certificate.
EOF
    REMOTE_WARNING_SHOWN=1
}

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
        warn_mutable_remote_install
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
        warn_mutable_remote_install
        fetch_script "$asset" > "$tmp_file"
        mv "$tmp_file" "$target"
    fi

    echo "Installed $asset"
}

install_glimmer_mcp() {
    local share_target="$SHARE_DIR/glimmer-mcp"
    local bin_wrapper="$BIN_DIR/glimmer-mcp"
    local venv_dir="$SHARE_DIR/.venv"

    # Install the Python source under SHARE_DIR (not BIN_DIR)
    if [ -f "$SCRIPT_DIR/glimmer-mcp" ]; then
        cp "$SCRIPT_DIR/glimmer-mcp" "$share_target"
    else
        local tmp_file
        tmp_file="$(mktemp)"
        warn_mutable_remote_install
        fetch_script "glimmer-mcp" > "$tmp_file"
        mv "$tmp_file" "$share_target"
    fi
    chmod +x "$share_target"
    echo "Installed glimmer-mcp (source)"

    # Create Glimmer-owned venv and install mcp
    if [ ! -f "$venv_dir/bin/python3" ]; then
        python3 -m venv "$venv_dir"
    fi
    "$venv_dir/bin/pip" install --quiet mcp
    echo "Installed mcp into Glimmer venv"

    # Write wrapper into BIN_DIR
    cat > "$bin_wrapper" <<'WRAPPER'
#!/usr/bin/env bash
exec "${HOME}/.local/share/glimmer/.venv/bin/python3" "${HOME}/.local/share/glimmer/glimmer-mcp" "$@"
WRAPPER
    chmod +x "$bin_wrapper"
    echo "Installed glimmer-mcp (wrapper)"
}

mkdir -p "$BIN_DIR"
mkdir -p "$SHARE_DIR"

for script in "${SCRIPTS[@]}"; do
    install_script "$script"
done

for asset in "${ASSETS[@]}"; do
    install_asset "$asset"
done

install_glimmer_mcp

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
echo "Use as MCP server: glimmer-mcp (add to ~/.claude/settings.json)"

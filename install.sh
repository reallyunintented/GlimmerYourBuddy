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
GLIMMER_MCP_PYPI_SPEC="${GLIMMER_MCP_PYPI_SPEC:-mcp==1.26.0}"
GLIMMER_GET_PIP_URL="${GLIMMER_GET_PIP_URL:-https://bootstrap.pypa.io/get-pip.py}"
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

fetch_url_to_file() {
    local url="$1"
    local target="$2"

    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$url" -o "$target"
        return
    fi

    if command -v wget >/dev/null 2>&1; then
        wget -qO "$target" "$url"
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
    local vendor_dir="$SHARE_DIR/vendor"
    local bootstrap_dir="$SHARE_DIR/.bootstrap"
    local venv_ready=0

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

    # Prefer a Glimmer-owned venv, but fall back to a vendored runtime when
    # python3-venv/ensurepip is unavailable on the host.
    if [ -x "$venv_dir/bin/python3" ] && "$venv_dir/bin/python3" -m pip --version >/dev/null 2>&1; then
        venv_ready=1
    else
        rm -rf "$venv_dir"
        if python3 -m venv "$venv_dir" >/dev/null 2>&1; then
            if [ -x "$venv_dir/bin/python3" ] && "$venv_dir/bin/python3" -m pip --version >/dev/null 2>&1; then
                venv_ready=1
            else
                rm -rf "$venv_dir"
                echo "python3 -m venv created an incomplete environment; falling back to a vendored MCP runtime." >&2
            fi
        else
            rm -rf "$venv_dir"
            echo "python3 -m venv unavailable; falling back to a vendored MCP runtime." >&2
        fi
    fi

    if [ "$venv_ready" -eq 1 ]; then
        rm -rf "$vendor_dir"
        "$venv_dir/bin/python3" -m pip install --quiet "$GLIMMER_MCP_PYPI_SPEC"
        echo "Installed $GLIMMER_MCP_PYPI_SPEC into Glimmer venv"
    else
        if python3 -m pip --version >/dev/null 2>&1; then
            :
        else
            local get_pip
            get_pip="$(mktemp)"
            mkdir -p "$bootstrap_dir"
            echo "Bootstrapping a Glimmer-local pip runtime..." >&2
            fetch_url_to_file "$GLIMMER_GET_PIP_URL" "$get_pip"
            if PYTHONUSERBASE="$bootstrap_dir" python3 "$get_pip" --user --break-system-packages >/dev/null 2>&1; then
                :
            elif PYTHONUSERBASE="$bootstrap_dir" python3 "$get_pip" --user >/dev/null 2>&1; then
                :
            else
                rm -f "$get_pip"
                echo "Error: failed to bootstrap a local pip runtime for glimmer-mcp." >&2
                exit 1
            fi
            rm -f "$get_pip"
        fi
        rm -rf "$vendor_dir"
        mkdir -p "$vendor_dir"
        PYTHONUSERBASE="$bootstrap_dir" python3 -m pip install --quiet --target "$vendor_dir" "$GLIMMER_MCP_PYPI_SPEC"
        echo "Installed $GLIMMER_MCP_PYPI_SPEC into Glimmer vendor runtime"
    fi

    # Write wrapper into BIN_DIR
    cat > "$bin_wrapper" <<'WRAPPER'
#!/usr/bin/env bash
share_dir="${HOME}/.local/share/glimmer"
if [ -x "${share_dir}/.venv/bin/python3" ]; then
    exec "${share_dir}/.venv/bin/python3" "${share_dir}/glimmer-mcp" "$@"
fi
if [ -d "${share_dir}/vendor" ]; then
    export PYTHONPATH="${share_dir}/vendor${PYTHONPATH:+:${PYTHONPATH}}"
    exec python3 "${share_dir}/glimmer-mcp" "$@"
fi
echo "Error: Glimmer MCP runtime is not installed. Re-run ./install.sh." >&2
exit 1
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

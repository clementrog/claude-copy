#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${HOME}/.local/bin"
KITTY_CONF="${HOME}/.config/kitty/kitty.conf"
ITERM2_SCRIPTS="${HOME}/Library/Application Support/iTerm2/Scripts/AutoLaunch"

# ── Detect terminal ──────────────────────────────────

detect_terminal() {
  if [ -d "/Applications/kitty.app" ] && [ -d "/Applications/iTerm.app" ]; then
    echo "both"
  elif [ -d "/Applications/kitty.app" ]; then
    echo "kitty"
  elif [ -d "/Applications/iTerm.app" ]; then
    echo "iterm2"
  else
    echo "none"
  fi
}

TERMINAL=$(detect_terminal)

if [ "$TERMINAL" = "none" ]; then
  echo "Error: Neither Kitty nor iTerm2 found in /Applications."
  echo "Install one of them first."
  exit 1
fi

# ── Install CLI script (Kitty only) ─────────────────

if [ "$TERMINAL" = "kitty" ] || [ "$TERMINAL" = "both" ]; then
  echo "Installing claude-copy-last CLI..."
  mkdir -p "$INSTALL_DIR"
  cp "$SCRIPT_DIR/claude-copy-last" "$INSTALL_DIR/claude-copy-last"
  chmod +x "$INSTALL_DIR/claude-copy-last"
  echo "  Installed to $INSTALL_DIR/claude-copy-last"

  if ! echo "$PATH" | tr ':' '\n' | grep -q "$INSTALL_DIR"; then
    echo ""
    echo "  WARNING: $INSTALL_DIR is not in your PATH."
    echo "  Add this to your shell profile (~/.zshrc or ~/.bashrc):"
    echo ""
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
  fi
fi

# ── Kitty setup ──────────────────────────────────────

if [ "$TERMINAL" = "kitty" ] || [ "$TERMINAL" = "both" ]; then
  echo ""
  echo "Kitty setup:"

  if [ ! -f "$KITTY_CONF" ]; then
    echo "  No kitty.conf found. Creating one..."
    mkdir -p "$(dirname "$KITTY_CONF")"
    cp "$SCRIPT_DIR/kitty/claude-copy.conf" "$KITTY_CONF"
    echo "  Created $KITTY_CONF"
  else
    NEEDS_UPDATE=false
    grep -q "allow_remote_control" "$KITTY_CONF" || NEEDS_UPDATE=true
    grep -q "listen_on" "$KITTY_CONF" || NEEDS_UPDATE=true
    grep -q "claude-copy-last" "$KITTY_CONF" || NEEDS_UPDATE=true

    if [ "$NEEDS_UPDATE" = true ]; then
      echo "  Add these lines to $KITTY_CONF:"
      echo ""
      cat "$SCRIPT_DIR/kitty/claude-copy.conf"
      echo ""
      echo "  Or append automatically:"
      echo "    cat \"$SCRIPT_DIR/kitty/claude-copy.conf\" >> \"$KITTY_CONF\""
    else
      echo "  Already configured."
    fi
  fi
fi

# ── iTerm2 setup ─────────────────────────────────────

if [ "$TERMINAL" = "iterm2" ] || [ "$TERMINAL" = "both" ]; then
  echo ""
  echo "iTerm2 setup:"

  mkdir -p "$ITERM2_SCRIPTS"
  cp "$SCRIPT_DIR/iterm2/claude_copy.py" "$ITERM2_SCRIPTS/claude_copy.py"
  echo "  Installed to $ITERM2_SCRIPTS/claude_copy.py"

  echo ""
  echo "  Remaining steps:"
  echo "  1. Enable Python API: Preferences > General > Magic > Enable Python API"
  echo "  2. Install runtime: Scripts > Manage > Install Python Runtime"
  echo "  3. Restart iTerm2"
  echo "  4. Bind keys in Preferences > Keys > Key Bindings:"
  echo "     Action: \"Invoke Script Function\""
  echo ""
  echo "     Cmd+Shift+C → claude_copy_response(session_id: id)"
  echo "     Cmd+Shift+P → claude_copy_plan(session_id: id)"
  echo "     Cmd+Shift+A → claude_copy_ask(session_id: id)"
fi

# ── Summary ──────────────────────────────────────────

echo ""
echo "Done! Restart your terminal to apply changes."
echo ""
echo "Shortcuts:"
echo "  Cmd+Shift+C  Copy last Claude response"
echo "  Cmd+Shift+P  Copy the plan"
echo "  Cmd+Shift+A  Copy last question + answer options"

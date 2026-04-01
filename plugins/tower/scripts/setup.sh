#!/usr/bin/env bash
# Tower - Install script
# Installs the tower binary and optionally configures terminal split shortcuts.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/bin"
SHELL_RC="$HOME/.zshrc"

echo "Tower - Live session mirror"
echo "==========================="
echo ""

# ── Core install ─────────────────────────────────────────────────────────

mkdir -p "$BIN_DIR"
cp "$SCRIPT_DIR/bin/tower" "$BIN_DIR/tower"
chmod +x "$BIN_DIR/tower"
echo "[ok] Installed tower to $BIN_DIR/tower"

# Ensure ~/bin is in PATH
if ! grep -q '\$HOME/bin' "$SHELL_RC" 2>/dev/null && ! grep -q '~/bin' "$SHELL_RC" 2>/dev/null; then
    echo '' >> "$SHELL_RC"
    echo '# Tower - live session mirror' >> "$SHELL_RC"
    echo 'export PATH="$HOME/bin:$PATH"' >> "$SHELL_RC"
    echo "[ok] Added ~/bin to PATH in $SHELL_RC"
fi

# Add alias if not present
if ! grep -q "alias tw=" "$SHELL_RC" 2>/dev/null; then
    echo "alias tw='tower'" >> "$SHELL_RC"
    echo "[ok] Added alias tw='tower' to $SHELL_RC"
else
    echo "[ok] Alias tw already exists"
fi

# ── Terminal integrations ────────────────────────────────────────────────

echo ""
echo "Detecting terminals..."

# Ghostty
GHOSTTY_CONFIG="$HOME/Library/Application Support/com.mitchellh.ghostty/config"
if [ -f "$GHOSTTY_CONFIG" ]; then
    if grep -q "tower" "$GHOSTTY_CONFIG" 2>/dev/null; then
        echo "[ok] Ghostty: tower keybinds already configured"
    else
        cat >> "$GHOSTTY_CONFIG" << 'EOF'

# Tower - live session mirror (Cmd+Shift+T to split, then type tw)
keybind = super+shift+t=new_split:right
EOF
        echo "[ok] Ghostty: added Cmd+Shift+T to split right"
        echo "     Tip: After splitting, type 'tw' in the new pane"
    fi
fi

# tmux (the cleanest integration - single keybind does split + run)
TMUX_CONF="$HOME/.tmux.conf"
if command -v tmux >/dev/null 2>&1; then
    if [ -f "$TMUX_CONF" ] && grep -q "tower" "$TMUX_CONF" 2>/dev/null; then
        echo "[ok] tmux: tower keybind already configured"
    else
        cat >> "$TMUX_CONF" << 'EOF'

# Tower - live session mirror (prefix + T to open tower in right split)
bind T split-window -h -c "#{pane_current_path}" "tower"
EOF
        echo "[ok] tmux: added prefix+T to open tower in right split"
        echo "     Run: tmux source-file ~/.tmux.conf"
    fi
fi

# iTerm2
ITERM_SCRIPTS="$HOME/Library/Application Support/iTerm2/Scripts"
if [ -d "/Applications/iTerm.app" ]; then
    mkdir -p "$ITERM_SCRIPTS"
    if [ -f "$ITERM_SCRIPTS/tower-split.py" ]; then
        echo "[ok] iTerm2: tower script already installed"
    else
        cat > "$ITERM_SCRIPTS/tower-split.py" << 'PYEOF'
#!/usr/bin/env python3
"""Open a right split pane running tower."""
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window
    if window:
        session = window.current_tab.current_session
        await session.async_split_pane(vertical=True, command="tower")

iterm2.run_until_complete(main)
PYEOF
        echo "[ok] iTerm2: installed tower-split.py script"
        echo "     Open iTerm2 > Scripts menu > tower-split"
        echo "     Or bind a key: Settings > Keys > Add > Run Script > tower-split.py"
    fi
fi

# Warp
WARP_LAUNCHES="$HOME/.warp/launch_configurations"
if [ -d "/Applications/Warp.app" ] || [ -d "$HOME/.warp" ]; then
    mkdir -p "$WARP_LAUNCHES"
    if [ -f "$WARP_LAUNCHES/tower.yaml" ]; then
        echo "[ok] Warp: tower launch config already exists"
    else
        cat > "$WARP_LAUNCHES/tower.yaml" << 'EOF'
---
name: Claude + Tower
windows:
  - tabs:
      - title: Dev
        layout:
          split_direction: horizontal
          panes:
            - {}
            - commands:
                - exec: tower
EOF
        echo "[ok] Warp: created 'Claude + Tower' launch configuration"
        echo "     Open via: Warp > Sessions > Launch Configurations > Claude + Tower"
    fi
fi

# Kitty (supports launch with command in splits natively)
KITTY_CONF="$HOME/.config/kitty/kitty.conf"
if command -v kitty >/dev/null 2>&1 || [ -f "$KITTY_CONF" ]; then
    if [ -f "$KITTY_CONF" ] && grep -q "tower" "$KITTY_CONF" 2>/dev/null; then
        echo "[ok] Kitty: tower keybind already configured"
    else
        mkdir -p "$(dirname "$KITTY_CONF")"
        cat >> "$KITTY_CONF" << 'EOF'

# Tower - live session mirror (Cmd+Shift+T to open tower in right split)
map cmd+shift+t launch --location=vsplit --cwd=current tower
EOF
        echo "[ok] Kitty: added Cmd+Shift+T to open tower in right split"
    fi
fi

# WezTerm (Lua config - adds a keybind to split + spawn tower)
WEZTERM_CONF="$HOME/.wezterm.lua"
WEZTERM_CONF_ALT="$HOME/.config/wezterm/wezterm.lua"
WEZTERM_TARGET=""
if [ -f "$WEZTERM_CONF" ]; then
    WEZTERM_TARGET="$WEZTERM_CONF"
elif [ -f "$WEZTERM_CONF_ALT" ]; then
    WEZTERM_TARGET="$WEZTERM_CONF_ALT"
elif command -v wezterm >/dev/null 2>&1; then
    WEZTERM_TARGET="$WEZTERM_CONF"
fi
if [ -n "$WEZTERM_TARGET" ]; then
    if [ -f "$WEZTERM_TARGET" ] && grep -q "tower" "$WEZTERM_TARGET" 2>/dev/null; then
        echo "[ok] WezTerm: tower keybind already configured"
    else
        cat >> "$WEZTERM_TARGET" << 'LUAEOF'

-- Tower - live session mirror (Cmd+Shift+T to open tower in right split)
-- Add this to your keys table:
-- { key = "T", mods = "CMD|SHIFT", action = wezterm.action.SplitHorizontal { args = { "tower" } } },
LUAEOF
        echo "[ok] WezTerm: added tower config comment to $WEZTERM_TARGET"
        echo "     Add the keybind line to your 'keys' table manually"
    fi
fi

# Zellij (tmux alternative - supports run command in new pane)
ZELLIJ_CONF="$HOME/.config/zellij/config.kdl"
if command -v zellij >/dev/null 2>&1; then
    if [ -f "$ZELLIJ_CONF" ] && grep -q "tower" "$ZELLIJ_CONF" 2>/dev/null; then
        echo "[ok] Zellij: tower keybind already configured"
    else
        echo "[ok] Zellij: detected"
        echo "     Run tower in a split:  zellij action new-pane -d right -- tower"
        echo "     Or add to config.kdl keybinds section:"
        echo '       bind "Alt t" { NewPane "Right" { command "tower"; }; }'
    fi
fi

# Windows Terminal (settings.json profile)
WIN_TERM_SETTINGS="${LOCALAPPDATA:-}/Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json"
if [ -n "${LOCALAPPDATA:-}" ] && [ -f "$WIN_TERM_SETTINGS" ] 2>/dev/null; then
    if grep -q "tower" "$WIN_TERM_SETTINGS" 2>/dev/null; then
        echo "[ok] Windows Terminal: tower profile already exists"
    else
        echo "[ok] Windows Terminal: detected"
        echo "     Add this action to your settings.json keybindings:"
        echo '       { "command": { "action": "splitPane", "split": "vertical", "commandline": "tower" }, "keys": "ctrl+shift+t" }'
    fi
fi

# ── Done ─────────────────────────────────────────────────────────────────

echo ""
echo "Done! Run: source ~/.zshrc"
echo ""
echo "Usage:"
echo "  tower          # Watch most recent session"
echo "  tower --list   # List recent sessions"
echo "  tower 1        # Watch most recent from list"
echo "  tw             # Alias for tower"
echo ""
echo "Quick start:"
echo "  1. Open a split pane in your terminal"
echo "  2. Left pane:  claude"
echo "  3. Right pane: tw"

#!/usr/bin/env bash
# Launch tower in a split pane for the current terminal.
# Detects the terminal emulator and uses the appropriate split command.
#
# Usage: launch-pane.sh [session-id]
# If no session-id, tower auto-detects the most recent session.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOWER_BIN="$HOME/bin/tower"
SESSION_ARG="${1:-}"
TOWER_CMD="$TOWER_BIN"
if [ -n "$SESSION_ARG" ]; then
    TOWER_CMD="$TOWER_BIN $SESSION_ARG"
fi

# Ensure tower is installed
if [ ! -x "$TOWER_BIN" ]; then
    echo "tower not found at $TOWER_BIN"
    echo "Run: bash $SCRIPT_DIR/setup.sh"
    exit 1
fi

TERMINAL=$(bash "$SCRIPT_DIR/detect-terminal.sh")

case "$TERMINAL" in
    tmux)
        tmux split-window -h -c "#{pane_current_path}" "$TOWER_CMD"
        echo "Launched tower in tmux right split"
        ;;
    zellij)
        zellij action new-pane -d right -- $TOWER_CMD
        echo "Launched tower in zellij right pane"
        ;;
    kitty)
        kitty @ launch --location=vsplit --cwd=current $TOWER_CMD
        echo "Launched tower in kitty right split"
        ;;
    iterm2)
        osascript -e "
            tell application \"iTerm2\"
                tell current session of current window
                    split vertically with same profile command \"$TOWER_CMD\"
                end tell
            end tell
        " 2>/dev/null
        echo "Launched tower in iTerm2 right split"
        ;;
    ghostty)
        # Ghostty doesn't support programmatic splits yet.
        # Use the keybind (Cmd+Shift+T) then type the command.
        echo "MANUAL_SPLIT"
        echo "Ghostty doesn't support programmatic pane splits yet."
        echo "Press Cmd+Shift+T to split, then type: tw${SESSION_ARG:+ $SESSION_ARG}"
        ;;
    wezterm)
        # WezTerm CLI can split panes
        wezterm cli split-pane --right -- $TOWER_CMD 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "Launched tower in WezTerm right split"
        else
            echo "MANUAL_SPLIT"
            echo "Open a split pane and run: tw${SESSION_ARG:+ $SESSION_ARG}"
        fi
        ;;
    warp)
        echo "MANUAL_SPLIT"
        echo "Warp: Use the 'Claude + Tower' launch config (Sessions menu)"
        echo "Or split with Cmd+D, then type: tw${SESSION_ARG:+ $SESSION_ARG}"
        ;;
    windows-terminal)
        echo "MANUAL_SPLIT"
        echo "Press Ctrl+Shift+T to split, then type: tw${SESSION_ARG:+ $SESSION_ARG}"
        ;;
    *)
        echo "MANUAL_SPLIT"
        echo "Open a new terminal pane and run: tw${SESSION_ARG:+ $SESSION_ARG}"
        ;;
esac

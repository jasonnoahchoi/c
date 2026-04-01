#!/usr/bin/env bash
# Detect the current terminal emulator and output its name.
# Used by tower commands to know how to launch split panes.

detect_terminal() {
    # tmux check first (user might be in tmux inside any terminal)
    if [ -n "$TMUX" ]; then
        echo "tmux"
        return
    fi

    # Zellij
    if [ -n "$ZELLIJ" ] || [ -n "$ZELLIJ_SESSION_NAME" ]; then
        echo "zellij"
        return
    fi

    # Ghostty
    if [ "$TERM_PROGRAM" = "ghostty" ]; then
        echo "ghostty"
        return
    fi

    # Kitty
    if [ "$TERM_PROGRAM" = "kitty" ] || [ -n "$KITTY_PID" ]; then
        echo "kitty"
        return
    fi

    # WezTerm
    if [ "$TERM_PROGRAM" = "WezTerm" ]; then
        echo "wezterm"
        return
    fi

    # iTerm2
    if [ "$TERM_PROGRAM" = "iTerm.app" ] || [ -n "$ITERM_SESSION_ID" ]; then
        echo "iterm2"
        return
    fi

    # Warp
    if [ "$TERM_PROGRAM" = "WarpTerminal" ]; then
        echo "warp"
        return
    fi

    # Windows Terminal
    if [ -n "$WT_SESSION" ]; then
        echo "windows-terminal"
        return
    fi

    echo "unknown"
}

detect_terminal

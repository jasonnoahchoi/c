---
description: Install tower CLI and configure terminal split-pane shortcuts
---

# Tower Setup

Install the tower binary and configure your terminal for split-pane shortcuts.

## What to do

Run the setup script:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
```

This will:
1. Install `tower` to `~/bin/`
2. Add `~/bin` to PATH if missing
3. Add `tw` alias to `.zshrc`
4. Auto-detect and configure shortcuts for: Ghostty, tmux, Kitty, iTerm2, WezTerm, Warp, Zellij, Windows Terminal

After setup, tell the user to run `source ~/.zshrc` or open a new terminal tab.

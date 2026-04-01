---
description: Install tower CLI with optional TUI mode and terminal shortcuts
argument-hint: "[--tui | --all]"
---

# Tower Setup

Install the tower binary with optional features.

## What to do

Ask the user which mode they want:

| Mode | Command | What it installs |
|------|---------|-----------------|
| Basic | `setup.sh` | tower binary, parser, alias (zero deps) |
| TUI | `setup.sh --tui` | + interactive TUI mode (installs textual) |
| All | `setup.sh --all` | + TUI + terminal split-pane shortcuts |

Then run the appropriate command:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh        # basic
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh --tui   # + TUI
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh --all   # everything
```

After setup, tell the user to run `source ~/.zshrc` or open a new terminal tab.

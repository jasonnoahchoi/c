---
name: play
description: "Launch the interactive TUI to browse, search, and navigate the conversation. Use when the user wants to search through what was said, browse tool calls, or explore the session interactively."
argument-hint: "[session-id]"
---

# Tower Play - Interactive Conversation Browser

Launch tower's interactive TUI in a split pane for browsing, searching, and navigating the conversation.

## When to trigger automatically

- User wants to search through the conversation ("can I search what we did?")
- User wants to browse or explore tool calls and diffs
- User asks to find something specific said earlier
- User wants to navigate the session interactively rather than just watch it stream

## What to do

1. Detect the user's terminal by running:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/detect-terminal.sh
   ```

2. Launch tower TUI in a split pane:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/launch-pane.sh --tui
   ```

3. If the output contains "MANUAL_SPLIT", show the user the manual instructions.

4. If the launch succeeded, remind the user of the keybindings:
   - `j`/`k` to scroll, `g`/`G` for top/bottom
   - `/` to search messages
   - `t` to toggle tool calls, `d` to toggle diffs
   - `Enter` to expand/collapse a tool call
   - `q` to quit

## If textual is not installed

Tell the user to install it:
```bash
pip install textual
```

## If tower is not installed

Run the setup first:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
```

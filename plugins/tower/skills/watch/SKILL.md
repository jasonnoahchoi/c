---
name: watch
description: "Launch a live conversation mirror in a split terminal pane. Use when the user can't see scrollback, lost context after /clear or /compact, or asks what was said earlier."
argument-hint: "[session-id]"
---

# Tower - Live Conversation Mirror

Launch tower in a split pane to mirror this session in real-time.

## When to trigger automatically

- User says they can't see scrollback or it's gone
- User asks "what did you say?" or "can you repeat that?" after a /clear
- User mentions losing context or not being able to scroll up
- User complains about terminal clearing or output disappearing

When you detect these situations, tell the user you're opening tower in a split pane so they can see the full conversation history, then follow the steps below.

## What to do

1. Detect the user's terminal by running:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/detect-terminal.sh
   ```

2. Launch tower in a split pane:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/launch-pane.sh
   ```

3. If the output contains "MANUAL_SPLIT", the terminal doesn't support programmatic splits. Show the user the manual instructions from the output.

4. If the launch succeeded, confirm to the user that tower is running in the split pane.

## If tower is not installed

Run the setup first:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
```

Then retry the launch.

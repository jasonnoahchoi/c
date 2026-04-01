---
description: Launch a live conversation mirror in a split terminal pane
argument-hint: "[session-id]"
---

# Tower - Live Conversation Mirror

Launch tower in a split pane to mirror this session in real-time.

## What to do

1. Detect the user's terminal by running:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/detect-terminal.sh
   ```

2. Get the current session ID by running:
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

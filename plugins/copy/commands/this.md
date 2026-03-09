---
description: Copy & export the last Claude response to clipboard or file
---

Copy & export the last Claude response to clipboard or file.

This command is handled by the claude-export.py UserPromptSubmit hook.
The hook intercepts this prompt before it reaches Claude.

If you're seeing this, the hook may not be registered. Check that the `copy` plugin is installed and enabled.

---
description: Install the optional statusline wrapper for enriched session metadata
---

## Setup Enriched Session Metadata

The `save` plugin automatically saves readable session transcripts to `~/.claude/sessions/` on every compact and session end. **No setup is required for basic functionality.**

### Optional: Enriched Metadata

For richer frontmatter (cost, context window, worktree, version), install the statusline sidecar wrapper:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup-statusline.sh
```

Then restart Claude Code.

### Metadata Tiers

**Basic (zero config):** session ID, timestamp, model, git branch, working directory

**Enriched (after setup):** all of the above plus cost (USD/duration/lines), context window usage, worktree info, Claude Code version

### Uninstall

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup-statusline.sh --uninstall
```

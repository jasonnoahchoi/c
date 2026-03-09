# c — Claude Code Conversation Tools

A marketplace-style plugin collection for working with Claude Code conversations.

## Plugins

### c-copy

Copy & export conversation responses to clipboard or file.

| Usage | Description |
|-------|-------------|
| `/c:this` | Copy last response to clipboard |
| `/c:this N` | Copy Nth most recent response |
| `/c:this -N` | Copy last N responses |
| `/c:this --all` | Copy full conversation |
| `/c:this -p N` | Copy last N rounds (prompt + response pairs) |
| `/c:this list [N]` | List recent N responses with previews |
| `/c:this find "term"` | Search responses |
| `-t` | Include thinking blocks |
| `-s <path>` | Save to file instead of clipboard |
| `-f md\|txt\|json` | Output format |

### c-save

Auto-save readable session transcripts to `~/.claude/sessions/` before compact/clear wipes terminal scrollback. Fires on `PreCompact` and `SessionEnd` events.

Each saved session is a markdown file with YAML frontmatter:

```yaml
---
sessionId: abc12345
timestamp: 2026-03-09T14:30:00
trigger: precompact
cwd: /Users/you/project
model: claude-opus-4-6
gitBranch: feature/cool-thing
---
```

**Basic mode** (zero config): Saves session ID, timestamp, model, git branch, cwd.

**Enriched mode** (optional): Run `/c-save:setup` to also capture cost, context window, worktree, and version data via a statusline sidecar wrapper.

## Install

```bash
claude plugin add /path/to/c
```

## Structure

```
c/
├── .claude-plugin/
│   └── marketplace.json     # Plugin registry
├── plugins/
│   ├── copy/                # c-copy: clipboard export
│   │   ├── .claude-plugin/plugin.json
│   │   ├── hooks/hooks.json
│   │   ├── scripts/claude-export.py
│   │   └── commands/this.md
│   └── save/                # c-save: session preservation
│       ├── .claude-plugin/plugin.json
│       ├── hooks/hooks.json
│       ├── scripts/save-session.py
│       ├── scripts/setup-statusline.sh
│       └── commands/setup.md
└── README.md
```

## Requirements

- Python 3.7+
- Claude Code with plugin support
- Clipboard utility: `pbcopy` (macOS), `xclip` (Linux), or `clip.exe` (WSL)

## License

MIT

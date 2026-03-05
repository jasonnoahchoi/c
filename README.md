# /c

A Claude Code plugin for copying and exporting conversation responses. Zero tokens, instant results.

## Install

```bash
claude plugin install --plugin-dir /path/to/c
```

Or add to your marketplace and install from there.

## Usage

```
/c                  Copy last assistant response to clipboard
/c 2                Copy 2nd most recent response
/c -3               Copy last 3 responses
/c -p 3             Copy last 3 rounds (user + assistant pairs)
/c --all            Copy full conversation
/c list [N]         List recent N responses (default 10)
/c find "term"      Search responses for matching text
```

### Flags (combinable)

```
-t, --think         Include thinking blocks in output
-s <filepath>       Save to file instead of clipboard
-f md|txt|json      Output format (default: txt for clipboard, md for -s)
```

### Examples

```
/c                          # Copy last response
/c --all -s conv.md         # Export full conversation to markdown file
/c -t -p 5                  # Last 5 rounds with thinking blocks
/c --all -t -s debug.md     # Full conversation with thinking, saved to file
/c -3 -f json               # Last 3 responses as JSON to clipboard
/c find "error"             # Search for responses mentioning "error"
```

## How it works

This plugin uses a `UserPromptSubmit` hook to intercept `/c` commands before they reach Claude. The hook parses the session transcript JSONL directly and delivers results to clipboard or file. No LLM tokens are consumed.

### Content filtering

The export automatically filters out noise from the transcript:

- **Skill injections** — skill content loaded via the Skill tool
- **Task notifications** — background task completion messages
- **Command wrappers** — skill invocation metadata
- **System reminders** — hook-injected context
- **Tool use/results** — only text and (optionally) thinking blocks are exported

## Plugin structure

```
c/
├── .claude-plugin/
│   └── plugin.json           # Plugin metadata
├── hooks/
│   └── hooks.json            # UserPromptSubmit hook registration
├── commands/
│   └── c.md                  # Slash command registration + fallback
├── scripts/
│   └── claude-export.py      # Export logic (Python 3, stdlib only)
└── README.md
```

## Requirements

- Python 3.7+
- Claude Code with plugin support
- Clipboard utility: `pbcopy` (macOS), `xclip` (Linux), or `clip.exe` (WSL)

## License

MIT
